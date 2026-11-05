# Architecture du projet DocMind AI

## Vue d'ensemble de l'architecture

```mermaid
flowchart TD
    ST[Streamlit] --> API[API DocMind]
    API --> SQL[(SQL - documents et métadonnées)]
    API --> FS[Stockage des fichiers]
    API --> ING[Service d'ingestion]
    ING --> PARSE[Parsing et chunking]
    PARSE --> SQLN[(SQL / DocStore - nœuds)]
    PARSE --> EMB[Embeddings]
    EMB --> Q[(Qdrant - chunks feuilles)]
    ST --> CHAT[Assistant RAG]
    CHAT --> RET[Retriever + reranker]
    RET --> Q
    RET --> SQLN
    RET --> LLM[LLM Groq]
```

## Composants principaux

- **Streamlit** : Interface utilisateur interactive.
- **Service d'ingestion** : Traitement, chunking hiérarchique et génération d'embeddings.
- **Qdrant** : Base de données vectorielle pour les nœuds feuilles.
- **DocStore / SQL** : Stockage persistant des nœuds parents et de la structure du document.
- **LLM Groq** : Moteur d'inférence pour la génération rapide de réponses.