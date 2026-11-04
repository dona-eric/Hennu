from typing import TypedDict
from typing_extensions import NotRequired
from langgraph.graph import StateGraph, END
from app.services.retrievers.retrieving import reranker_tool
from app.services.llms.endpoint import client_groq
from app.core.loger import setup_logging

logger = setup_logging()


# create l'etat de l'agent

class AgentState(TypedDict):
    user_query: str
    rewritten_user_query: NotRequired[str]
    context: NotRequired[str]
    intention: NotRequired[str]
    reponse: NotRequired[str]


def analyse_query_intention_with_groq(query: str):
    llm = client_groq.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {'role': "system",
             'content': "Analyse la question de l'utilisateur, identifie de quoi il est question, s'il s'agit d'un contentieux, d'une loi , d'un code pénal ou non"
             },

            {"role":"user", 
            'content':query
            }
        ],
        temperature=0.0
    )

    return llm.choices[0].message.content.strip()


# personalisation de l'agent 

def customer_agent():
    """Construit et compile le graphe d'état LangGraph pour le RAG douanier."""

    workflow_state = StateGraph(
        state_schema=AgentState
        )
    
    tool = reranker_tool()

    query_engine = tool.query_engine

    # Step 1: Analyse et Optimisation de la requete utilisateur

    def analyse_query(state: AgentState):

        logger.info(f"1- Analyse de la requete uitilisateur")
        question = state["user_query"]
        intention = analyse_query_intention_with_groq(question)

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

        response = client_groq.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        rewritten_question = response.choices[0].message.content.strip()
        
        logger.info(f"Requête user réécrite : {rewritten_question}")
        return {
            "rewritten_user_query": rewritten_question,
            "intention": intention
            }


    # step 2: etape de recuperation des reponses de qdrant

    def retrieve_and_rerank(state: AgentState):

        logger.info(f"[Agent of Retrieval]")
        query = state["rewritten_user_query"]

        response_obj = query_engine.query(query)
        context_obj = str(response_obj)
        logger.info(f"[Agent Committe]")
        return {"context": context_obj}


    def generate_final_response(state: AgentState):
        logger.info("Agent [Generate] : Rédaction de la réponse juridique...")
        question = state["question"]
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
        
        response = client_groq.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        return {"response": response.choices[0].message.content.strip()}

    # Ajout des nœuds au graphe LangGraph
    workflow_state.add_node("analyze_query", analyse_query)
    workflow_state.add_node("retrieve_docs", retrieve_and_rerank)
    workflow_state.add_node("generate_response", generate_final_response)

    # Définition des liaisons (flux d'exécution)
    workflow_state.set_entry_point("analyze_query")
    workflow_state.add_edge("analyze_query", "retrieve_docs")
    workflow_state.add_edge("retrieve_docs", "generate_response")
    workflow_state.add_edge("generate_response", END)

    # Compilation du graphe
    return workflow_state.compile()