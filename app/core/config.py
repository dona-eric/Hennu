import os
import dotenv


### chargement des données keys de l'environnement virtual
dotenv.load_dotenv()

# KEYS LLAMA CLOUD
# os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-llamaindex-bypass"
QDRANT_API_KEY=os.getenv("QDRANT_API_KEY")
QDRANT_URL="https://39a12a7c-bbbd-4f34-b9b8-1712e83f723a.us-west-1-0.aws.cloud.qdrant.io"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TOKEN_HUGGINGFACE = os.getenv("HUGGINGFACE_TOKEN")
# REPO_ID="Qwen/Qwen3.8-2.4T-A95B"
IMOLE_API_KEY = os.getenv("IMOLE_API_KEY")
IMOLE_BASE_URL = "https://api.imole.app/v1"
MODEL_IMOLE_DEFAULT="gpt-5.6-luna"
EMBEDDING_DIMENSION =384
EMBEDDING_MODEL_NAME="intfloat/multilingual-e5-small"
DATALAB_API_KEY = os.getenv("marker_api_key")
API_KEY_GROQ = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")