from typing import TypedDict
from typing_extensions import NotRequired
from langgraph.graph import StateGraph, END
from app.services.retrievers.retrieving import create_retriever, search_reranking, reranker_tool
from app.services.llms.endpoint import client_openai, nvidia_client
from app.core.loger import setup_logging

logger = setup_logging()


# create l'etat de l'agent

class AgentState(TypedDict):
    user_query: str
    rewritten_user_query: NotRequired[str]
    context: NotRequired[str]
    intention: NotRequired[str]
    reponse: NotRequired[str]
    sources: NotRequired[list]
    reponse: NotRequired[str]

def analyse_query_intention(query: str):
    prompt = f"""
            Tu es un expert en législation douanière béninoise.

            Analyse la question de l'utilisateur.

            Identifie :
            - Le domaine juridique concerné.
            - L'intention de l'utilisateur.
            - La présence éventuelle d'un contentieux.
            - La référence juridique recherchée.

            Ne réponds pas à la question.
            Retourne uniquement une classification concise.

            Question :
            {query}
        """

    response = nvidia_client.complete(prompt)

    return response.text.strip()


# personalisation de l'agent 

def customer_agent():
    """Construit et compile le graphe d'état LangGraph pour le RAG douanier."""

    workflow_state = StateGraph(
        state_schema=AgentState
        )
    
    retriever = create_retriever()

    reranker = search_reranking()

    # Step 1: Analyse et Optimisation de la requete utilisateur

    def analyse_query(state: AgentState):

        logger.info(f"1- Analyse de la requete uitilisateur")
        question = state["user_query"]
        intention = analyse_query_intention(question)

        prompt = f"""
            Tu es un assistant expert en législation douanière (Code des Douanes du Bénin).
            
            Intention Utilisateur:
            {intention}
            Reformule la question suivante pour qu'elle intègre le vocabulaire juridique
            Reformule la question suivante pour optimiser la recherche
            dans une base documentaire juridique.

            Règles :
            - Conserve le sens exact de la question.
            - Utilise le vocabulaire juridique et douanier approprié.
            - N'ajoute aucune information qui n'est pas présente.
            - Retourne uniquement la question reformulée.

            Question originale :
            {question}
            """

        response = nvidia_client.complete(
            prompt=prompt
        )
        rewritten_question = response.text.strip()
        
        logger.info(f"Requête user réécrite : {rewritten_question}")
        return {
            "rewritten_user_query": rewritten_question,
            "intention": intention
            }


    # step 2: etape de recuperation des reponses de qdrant

    def retrieve_and_rerank_nodes(state: AgentState):

        logger.info(f"[Agent of Retrieval]")
        query = state.get(
            "rewritten_user_query",
            state['user_query'],
        )
        nodes = reranker_tool(
            retriever=retriever,
            reranker=reranker,
            query=query,
        )

        if not nodes:
            logger.warning("Aucun document pertinent trouvé.")

        return {
            "context": "",
            "sources": [],
        }

        # Construction du contexte juridique
        context_parts = []
        sources = []

        for rank, node in enumerate(nodes, start=1):

            content = node.get_content()
            metadata = node.metadata or {}

            article = metadata.get("article", "Non précisé")
            source = metadata.get(
                "file_name",
                metadata.get("source", "Source inconnue"),
            )

            score = node.score

            context_parts.append(
                f"""
                [Document {rank}]
                Article : {article}
                Source : {source}
                Score : {score}

                Contenu :
                {content}
                """
            )

            sources.append({
                "rank": rank,
                "article": article,
                "source": source,
                "score": score,
                "content": content,
            })

        return {
            "context": "\n\n".join(context_parts),
            "sources": sources,
        }


    def generate_final_response(state: AgentState):
        logger.info("Agent [Generate] : Rédaction de la réponse juridique...")
        question = state['user_query']
        context = state["context"]
        
        prompt = f"""
        Tu es un assistant juridique de pointe spécialisé dans le Code des Douanes de la République du Bénin. 
        Tu t'adresses à des commissaires agréés et des professionnels de la douane exigeants.
        
        Règles de réponse :
        1. Base-toi exclusivement sur le contexte juridique fourni ci-dessous.
        2. Cite clairement les articles, chapitres ou sections applicables.
        3. Sois précis, rigoureux et professionnel dans l'explication des procédures, régimes ou contentieux douaniers.
        
        Contexte juridique extrait :
        {context}
        
        Question de l'utilisateur :
        {question}
        """
        
        response = client_openai.complete(
            prompt=prompt
        )

        return {"response": response.text.strip()}

    # Ajout des nœuds au graphe LangGraph
    workflow_state.add_node("analyze_query", analyse_query)
    workflow_state.add_node("retrieve_docs", retrieve_and_rerank_nodes)
    workflow_state.add_node("generate_response", generate_final_response)

    # Définition des liaisons (flux d'exécution)
    workflow_state.set_entry_point("analyze_query")
    workflow_state.add_edge("analyze_query", "retrieve_docs")
    workflow_state.add_edge("retrieve_docs", "generate_response")
    workflow_state.add_edge("generate_response", END)

    # Compilation du graphe
    return workflow_state.compile()