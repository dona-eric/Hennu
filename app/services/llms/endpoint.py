from mpmath.libmp import from_man_exp
from typing import Any, Dict, List
from app.core.config import NVIDIA_API_KEY
from app.core.loger import setup_logging
from openai import OpenAI
from llama_index.llms.openai_like import OpenAILike
from llama_index.llms.nvidia import NVIDIA
from llama_index.core.settings import Settings

logger = setup_logging()

SYSTEM_PROMPT = (
    "Tu es un assistant spécialisé dans la réglementation douanière",
    "Tu es un agent ia qui repond dans un contexte béninois douanier",
    "Tu dois te comportement également comme un agent de la douane ou un commissaire agrée par la douane en charge des affaires portuaires, transports,logistique", 
    "portuaire du Bénin (Port Autonome de Cotonou, Douanes Béninoises). "
    "Tu dois repondre en français",
    "Réponds UNIQUEMENT à partir des extraits fournis dans le contexte ci-dessous.\n\n"
    "Règles strictes :\n"
    "1. Si le contexte ne permet pas de répondre avec certitude, dis-le clairement sans inventer.\n"
    "2. Cite systématiquement la source (nom du document) et le numéro d'article exact "
    "pour chaque affirmation importante.\n"
    "3. Adopte un ton professionnel, précis et juridiquement rigoureux."
)


client_openai = OpenAILike(
    model="openai/gpt-oss-20b",
    api_base="https://integrate.api.nvidia.com/v1",
    api_key = NVIDIA_API_KEY,
    is_chat_model=True,
    timeout=300
)


nvidia_client = OpenAILike(
    model="mistralai/mistral-large-4-1t-a52b",
    api_base="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    is_chat_model=True,
    timeout=300
)
Settings.llm = client_openai

