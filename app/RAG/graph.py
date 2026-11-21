"""Graphe RAG agentic de l'assistant douanier Orion.

    analyze_query -> retrieve_docs -> grade_documents
        suffisant                     -> generate_response
        insuffisant, essai restant    -> refine_query -> retrieve_docs
        insuffisant, plus d'essai     -> generate_response
    generate_response -> verify_answer
        vérifiée ou plus d'essai      -> FIN
        non vérifiée, essai restant   -> generate_response (révision)
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph
from typing_extensions import NotRequired

from app.core.loger import setup_logging
from app.RAG.helpers import build_context, invalid_citations, merge_sources, numbered_excerpts, parse_json_object, source_from_node
from app.services.configer.call_config import get_config
from app.services.llms.endpoint import ask_llm, fallback_llm, fast_llm, main_llm
from app.services.llms.prompts_manager import create_default_prompt_manager
from app.services.retrievers.reranker import IReranker
from app.services.retrievers.retrieving import (
    ArticleLibrary,
    IRetriever,
    find_articles_in_question,
    get_parent_article,
)

logger = setup_logging()

MAX_CONTENT_CHARS = 6000  # limite de taille d'un document envoyé au LLM

# Noms des templates (voir app/services/llms/prompts_manager.py)
SYSTEM_TEMPLATE = "rag_agentic_system_prompt"
REWRITE_TEMPLATE = "rag_query_rewrite"
REFINE_TEMPLATE = "rag_query_refine"
GRADER_TEMPLATE = "rag_document_grader"
VERIFIER_TEMPLATE = "rag_answer_verifier"
REVISION_TEMPLATE = "rag_answer_revision"

NO_CONTEXT_ANSWER = (
    "Je n'ai trouvé aucun texte pertinent dans la base documentaire "
    "pour répondre à cette question. Pouvez-vous la reformuler ou la préciser ?"
)
UNVERIFIED_NOTE = (
    "\n\n> ⚠️ Certaines affirmations de cette réponse n'ont pas pu être "
    "vérifiées dans les sources. Consultez les extraits cités avant de "
    "vous y fier."
)


class AgentState(TypedDict):
    """État partagé entre les étapes du graphe.

    Attention : un nœud ne peut renvoyer que des clés déclarées ici,
    sinon LangGraph les ignore silencieusement.
    """

    user_query: str
    rewritten_user_query: NotRequired[str]
    tried_queries: NotRequired[list[str]]
    search_attempts: NotRequired[int]
    candidate_count: NotRequired[int]
    sources: NotRequired[list]
    context: NotRequired[str]
    documents_sufficient: NotRequired[bool]
    grading_reason: NotRequired[str]
    response: NotRequired[str]
    generation_attempts: NotRequired[int]
    verification_issues: NotRequired[list[str]]
    grounded: NotRequired[bool]
    needs_revision: NotRequired[bool]


def customer_agent():
    """Construit le graphe RAG agentic (rechercher, évaluer, réessayer, vérifier)."""

    # Chargés une seule fois au démarrage
    config = get_config()
    settings = config.section("rag-agentic-config")
    max_search_attempts = int(settings.get("max_search_attempts", 2))
    max_generation_attempts = int(settings.get("max_generation_attempts", 2))
    grading_chars = int(settings.get("grading_excerpt_chars", 800))
    verification_chars = int(settings.get("verification_excerpt_chars", 2000))

    retriever = IRetriever.from_config(config)
    reranker = IReranker.from_config(config=config)
    library = ArticleLibrary()  # rechargée quand la base documentaire change

    prompts = create_default_prompt_manager()
    prompt_version = settings.get("prompt_version")
    system_template = prompts.get_template(SYSTEM_TEMPLATE, prompt_version)
    logger.info(f"Prompt système : {SYSTEM_TEMPLATE} v{system_template.version}")

    # Nœuds

    def analyse_query(state: AgentState):
        """Reformule la question avec le vocabulaire douanier."""
        logger.info("[analyse] Reformulation de la question")
        question = state["user_query"]

        prompt = prompts.render_template(REWRITE_TEMPLATE, question=question)
        query = ask_llm(fast_llm, prompt) or question
        logger.info(f"Requête : {query}")
        return {"rewritten_user_query": query, "tried_queries": [query]}

    def retrieve_docs(state: AgentState):
        """Cherche les textes : articles cités + recherche par le sens."""
        attempt = state.get("search_attempts", 0) + 1
        question = state["user_query"]
        query = state.get("rewritten_user_query", question)
        logger.info(f"[recherche {attempt}] {query}")

        library.refresh()
        found = []

        # La question cite un article précis : on le prend directement
        for article_node in find_articles_in_question(question, library.article_index):
            source = source_from_node(article_node, max_chars=MAX_CONTENT_CHARS)
            source["direct"] = True
            found.append(source)

        # Recherche par le sens (Qdrant + reranker)
        for node in reranker.rerank(query, retriever.retrieve(query)):
            # On remplace le passage par l'article complet quand c'est possible
            parent = get_parent_article(node, library.docstore)
            found.append(source_from_node(parent, node.score, MAX_CONTENT_CHARS))

        # Les documents jugés pertinents aux essais précédents sont conservés
        candidates = merge_sources(state.get("sources", []), found)
        logger.info(f"{len(candidates)} documents candidats.")
        return {
            "sources": candidates,
            "search_attempts": attempt,
            "candidate_count": len(candidates),
        }

    def grade_documents(state: AgentState):
        """Garde les documents utiles et juge s'ils suffisent pour répondre."""
        candidates = state.get("sources", [])
        if not candidates:
            return _graded([], sufficient=False, reason="Aucun document trouvé.")

        prompt = prompts.render_template(
            GRADER_TEMPLATE,
            question=state["user_query"],
            documents=numbered_excerpts(candidates, grading_chars),
        )
        verdict = parse_json_object(ask_llm(fast_llm, prompt))

        if verdict is None:
            # Évaluation illisible : on ne bloque pas, on garde tout
            logger.warning("Évaluation des documents illisible : tout est conservé.")
            return _graded(candidates, sufficient=True, reason="")

        relevant = _numbers(verdict.get("relevant", []))
        kept = [
            source
            for index, source in enumerate(candidates, start=1)
            if index in relevant or source.get("direct")
        ]
        sufficient = bool(verdict.get("sufficient")) and bool(kept)
        reason = str(verdict.get("reason", ""))
        logger.info(
            f"[évaluation] {len(kept)}/{len(candidates)} pertinents, "
            f"suffisant={sufficient} : {reason}"
        )
        return _graded(kept, sufficient, reason)

    def refine_query(state: AgentState):
        """Reformule autrement la recherche, à partir de ce qui manquait."""
        tried = state.get("tried_queries", [])
        prompt = prompts.render_template(
            REFINE_TEMPLATE,
            question=state["user_query"],
            tried_queries="\n".join(f"- {query}" for query in tried),
            reason=state.get("grading_reason") or "documents peu pertinents",
        )
        query = ask_llm(fast_llm, prompt).strip() or state["user_query"]
        logger.info(f"[nouvel essai] {query}")
        return {"rewritten_user_query": query, "tried_queries": [*tried, query]}

    def generate_response(state: AgentState):
        """Rédige la réponse (ou la révise après une vérification échouée)."""
        attempt = state.get("generation_attempts", 0) + 1
        context = state.get("context", "")
        logger.info(f"[rédaction {attempt}]")

        if not context:
            return {"response": NO_CONTEXT_ANSWER, "generation_attempts": attempt}

        message = state["user_query"]
        issues = state.get("verification_issues") or []
        if attempt > 1 and issues:
            message = prompts.render_template(
                REVISION_TEMPLATE,
                question=state["user_query"],
                issues="\n".join(f"- {issue}" for issue in issues),
            )

        answer = ask_llm(
            main_llm,
            message,
            system_prompt=system_template.render(context=context),
            fallback_llm=fallback_llm,
        )
        return {"response": answer, "generation_attempts": attempt}

    def verify_answer(state: AgentState):
        """Vérifie les citations [n] puis l'ancrage de la réponse dans les sources."""
        answer = state.get("response", "")
        sources = state.get("sources", [])
        attempt = state.get("generation_attempts", 1)

        if not sources or answer == NO_CONTEXT_ANSWER:
            return _verified(grounded=True, issues=[], needs_revision=False)

        # Contrôle sans LLM : chaque [n] doit désigner une source existante
        issues = [
            f"La citation [{number}] ne correspond à aucune source "
            f"(sources numérotées de 1 à {len(sources)})."
            for number in invalid_citations(answer, len(sources))
        ]

        # Contrôle par le LLM : chaque affirmation est-elle dans les sources ?
        prompt = prompts.render_template(
            VERIFIER_TEMPLATE,
            sources=numbered_excerpts(sources, verification_chars),
            answer=answer,
        )
        verdict = parse_json_object(ask_llm(fast_llm, prompt))
        if verdict is None:
            logger.warning("Vérification illisible : citations seules contrôlées.")
        elif not verdict.get("grounded", True):
            issues += [str(claim) for claim in verdict.get("unsupported", []) if claim]
            if not issues:
                issues.append("Des affirmations ne sont pas appuyées par les sources.")

        grounded = not issues
        needs_revision = not grounded and attempt < max_generation_attempts
        logger.info(f"[vérification] fondée={grounded}, révision={needs_revision}")

        update = _verified(grounded, issues, needs_revision)
        # Dernier essai non vérifié : on prévient l'utilisateur
        if not grounded and not needs_revision:
            update["response"] = answer + UNVERIFIED_NOTE
        return update

    # Aiguillages (arêtes conditionnelles)

    def after_grading(state: AgentState) -> str:
        if state.get("documents_sufficient"):
            return "generate"
        if state.get("search_attempts", 1) < max_search_attempts:
            return "retry"
        return "generate"  # plus d'essai : on répond avec ce qu'on a

    def after_verification(state: AgentState) -> str:
        return "revise" if state.get("needs_revision") else "end"

    # Construction du graphe

    workflow = StateGraph(state_schema=AgentState)
    workflow.add_node("analyze_query", analyse_query)
    workflow.add_node("retrieve_docs", retrieve_docs)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("refine_query", refine_query)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("verify_answer", verify_answer)

    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve_docs")
    workflow.add_edge("retrieve_docs", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        after_grading,
        {"generate": "generate_response", "retry": "refine_query"},
    )
    workflow.add_edge("refine_query", "retrieve_docs")
    workflow.add_edge("generate_response", "verify_answer")
    workflow.add_conditional_edges(
        "verify_answer",
        after_verification,
        {"revise": "generate_response", "end": END},
    )

    return workflow.compile()


def _graded(sources: list[dict], sufficient: bool, reason: str) -> dict:
    """Mise à jour de l'état après l'évaluation des documents."""
    return {
        "sources": sources,
        "context": build_context(sources),
        "documents_sufficient": sufficient,
        "grading_reason": reason,
    }


def _numbers(values) -> set[int]:
    """Numéros d'extraits renvoyés par le LLM (1, "1" ou 1.0 sont acceptés)."""
    numbers = set()
    for value in values if isinstance(values, list) else []:
        try:
            numbers.add(int(value))
        except (TypeError, ValueError):
            continue
    return numbers


def _verified(grounded: bool, issues: list[str], needs_revision: bool) -> dict:
    return {
        "grounded": grounded,
        "verification_issues": issues,
        "needs_revision": needs_revision,
    }
