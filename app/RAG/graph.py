from typing import TypedDict

from langgraph.graph import END, StateGraph
from typing_extensions import NotRequired

from app.core.loger import setup_logging
from app.services.configer.call_config import get_config
from app.services.llms.endpoint import (
    ask_llm,
    fallback_llm,
    fast_llm,
    main_llm,
)
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

NO_CONTEXT_ANSWER = (
    "Je n'ai trouvé aucun texte pertinent dans la base documentaire "
    "pour répondre à cette question. Pouvez-vous la reformuler ou la préciser ?"
)


class AgentState(TypedDict):
    """État partagé entre les étapes du graphe.

    Attention : un nœud ne peut renvoyer QUE des clés déclarées ici,
    sinon LangGraph les ignore silencieusement.
    """
    user_query: str
    rewritten_user_query: NotRequired[str]
    context: NotRequired[str]
    sources: NotRequired[list]
    response: NotRequired[str]


def customer_agent():
    """Construit le graphe RAG douanier : reformuler -> rechercher -> répondre."""

    # Chargés une seule fois au démarrage
    config = get_config()
    retriever = IRetriever.from_config(config)
    reranker = IReranker.from_config(config=config)
    # Rechargée automatiquement quand la base documentaire change
    library = ArticleLibrary()

    # Prompts versionnés : la version du prompt système vient du YAML
    prompts = create_default_prompt_manager()
    prompt_version = config.section("rag-agentic-config").get("prompt_version")
    system_template = prompts.get_template(SYSTEM_TEMPLATE, prompt_version)
    logger.info(f"Prompt système : {SYSTEM_TEMPLATE} v{system_template.version}")

    # Étape 1 : reformuler la question avec le vocabulaire douanier
    def analyse_query(state: AgentState):
        logger.info("[1/3] Reformulation de la question")
        question = state["user_query"]

        prompt = prompts.render_template(REWRITE_TEMPLATE, question=question)
        rewritten_question = ask_llm(fast_llm, prompt) or question
        logger.info(f"Question reformulée : {rewritten_question}")
        return {"rewritten_user_query": rewritten_question}

    # Étape 2 : chercher les textes pertinents
    def retrieve_and_rerank_nodes(state: AgentState):
        logger.info("[2/3] Recherche des textes pertinents")
        question = state["user_query"]
        query = state.get("rewritten_user_query", question)

        context_parts = []
        sources = []
        seen_ids = set()

        def add_document(text_node, score=None):
            """Ajoute un document au contexte (une seule fois par article)."""
            if text_node.node_id in seen_ids:
                return
            seen_ids.add(text_node.node_id)

            metadata = text_node.metadata or {}
            article = metadata.get("article_title") or "Passage"
            document = metadata.get("document_title") or metadata.get("source", "Source inconnue")
            chapter = metadata.get("chapter") or ""
            content = text_node.get_content()[:MAX_CONTENT_CHARS]

            # Le numéro [n] est celui que le LLM cite et que l'interface affiche
            context_parts.append(
                f"[{len(sources) + 1}]\n"
                f"Texte : {document}\n"
                f"Chapitre : {chapter}\n"
                f"{article}\n\n"
                f"{content}"
            )
            sources.append({
                "title": f"{article} — {document}",
                "article": article,
                "source": metadata.get("source"),
                "document_id": metadata.get("document_id"),
                "score": score,
                "content": content,
            })

        library.refresh()

        # a) La question cite un article précis : on va le chercher directement
        direct_articles = find_articles_in_question(question, library.article_index)
        for article_node in direct_articles:
            add_document(article_node)
        if direct_articles:
            logger.info(f"{len(direct_articles)} article(s) trouvé(s) par leur numéro.")

        # Recherche par le sens (Qdrant + reranker), en complément
        for node in reranker.rerank(query, retriever.retrieve(query)):
            # On remplace le passage par l'article complet quand c'est possible
            add_document(get_parent_article(node, library.docstore), score=node.score)

        if not sources:
            logger.warning("Aucun document pertinent trouvé.")

        logger.info(f"{len(sources)} documents envoyés au LLM.")
        return {"context": "\n\n---\n\n".join(context_parts), "sources": sources}

    # Étape 3 : rédiger la réponse à partir du contexte
    def generate_final_response(state: AgentState):
        logger.info("[3/3] Rédaction de la réponse")
        context = state.get("context", "")

        if not context:
            return {"response": NO_CONTEXT_ANSWER}

        # Le contexte est dans le prompt système
        answer = ask_llm(
            main_llm,
            state["user_query"],
            system_prompt=system_template.render(context=context),
            fallback_llm=fallback_llm,
        )
        return {"response": answer}

    # Construction du graphe
    workflow = StateGraph(state_schema=AgentState)
    workflow.add_node("analyze_query", analyse_query)
    workflow.add_node("retrieve_docs", retrieve_and_rerank_nodes)
    workflow.add_node("generate_response", generate_final_response)

    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve_docs")
    workflow.add_edge("retrieve_docs", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()
