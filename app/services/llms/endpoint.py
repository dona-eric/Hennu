"""Clients LLM (section « llm » du YAML).

- main_llm     : modèle principal, pour rédiger la réponse finale
- fast_llm     : petit modèle rapide, pour reformuler la question
- fallback_llm : modèle de secours si le principal est indisponible
                 (provider_second s'il a une clé API, sinon fast_llm)
"""

from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.core.settings import Settings
from llama_index.llms.openai_like import OpenAILike

from app.core.loger import setup_logging
from app.services.configer.call_config import get_config

logger = setup_logging()

# Chaque fournisseur expose une API compatible OpenAI
PROVIDER_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

# Les prompts sont dans app/services/llms/prompts_manager.py


def build_llm(
    provider: dict[str, Any],
    model: str | None = None,
    max_retries: int = 2,
) -> OpenAILike:
    """Crée un client LLM à partir d'une entrée `llm.<provider>` du YAML.

    `model` permet de choisir un autre modèle du même fournisseur
    (par exemple le modèle rapide).
    """
    name = provider["name"]
    params = provider.get("params") or {}

    if name not in PROVIDER_BASE_URLS:
        raise ValueError(f"Fournisseur LLM inconnu : « {name} »")

    additional_kwargs = {}
    if params.get("top_p") is not None:
        additional_kwargs["top_p"] = params["top_p"]

    return OpenAILike(
        model=model or params["model_name"],
        api_base=PROVIDER_BASE_URLS[name],
        api_key=params.get("api_key"),
        temperature=params.get("temperature", 0.2),
        max_tokens=params.get("max_tokens"),
        additional_kwargs=additional_kwargs,
        is_chat_model=True,
        timeout=120,
        max_retries=max_retries,
    )


def ask_llm(
    llm: OpenAILike,
    prompt: str,
    system_prompt: str | None = None,
    fallback_llm: OpenAILike | None = None,
) -> str:
    """Envoie une question au LLM et renvoie le texte de sa réponse.

    Si le modèle est indisponible (surcharge, quota...) et qu'un modèle
    de secours est fourni, la question lui est envoyée à la place.
    """
    messages = []
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    messages.append(ChatMessage(role="user", content=prompt))

    try:
        response = llm.chat(messages)
    except Exception as error:
        if fallback_llm is None:
            raise
        logger.warning(
            f"{llm.model} indisponible ({error}). Bascule sur {fallback_llm.model}."
        )
        response = fallback_llm.chat(messages)

    return (response.message.content or "").strip()


# ------------------------------------------------------------------
# Création des clients à partir du YAML
# ------------------------------------------------------------------

_llm_config = get_config().section("llm")
_first = _llm_config["provider_first"]
_second = _llm_config.get("provider_second") or {}

# Pas de nouvel essai : en cas d'échec, on bascule tout de suite sur le secours
main_llm = build_llm(_first, max_retries=0)
fast_llm = build_llm(_first, model=(_first.get("params") or {}).get("fast_model_name"))

# Le second fournisseur n'est utilisé que si sa clé API est définie dans le .env
if (_second.get("params") or {}).get("api_key"):
    fallback_llm = build_llm(_second)
else:
    fallback_llm = fast_llm

Settings.llm = main_llm

logger.info(
    "LLM : principal=%s, rapide=%s, secours=%s",
    main_llm.model,
    fast_llm.model,
    fallback_llm.model,
)
