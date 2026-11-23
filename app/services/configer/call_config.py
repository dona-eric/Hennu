"""Chargement de la configuration du système RAG (app/core/free_config.yml).

Les valeurs de la forme "${NOM}" sont remplacées par la variable
d'environnement correspondante (lue depuis le fichier .env).
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import dotenv
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "core" / "free_config.yml"

# Repère les "${NOM_DE_VARIABLE}" dans les valeurs du YAML
ENV_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Les clés secrètes (QDRANT_API_KEY, GEMINI_API_KEY...) sont dans le .env
dotenv.load_dotenv()


def _resolve_env(value: Any) -> Any:
    """Remplace récursivement les "${NOM}" par la variable d'environnement.

    Une variable absente du .env devient une chaîne vide.
    """
    if isinstance(value, str):
        return ENV_VARIABLE.sub(lambda match: os.getenv(match.group(1), ""), value)
    if isinstance(value, dict):
        return {key: _resolve_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    return value


class Configuration:
    """Lit le fichier YAML de configuration."""

    def __init__(self, config_path: Path | str = CONFIG_PATH) -> None:
        self.config_path = Path(config_path)
        self.data: dict[str, Any] = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Charge le fichier YAML et renvoie son contenu sous forme de dict."""
        if not self.config_path.is_file():
            raise FileNotFoundError(
                f"Le fichier de configuration {self.config_path} est introuvable."
            )

        with self.config_path.open(encoding="utf-8") as file:
            config = yaml.safe_load(file)

        if config is None:
            return {}
        if not isinstance(config, dict):
            raise ValueError(
                f"Le fichier de configuration {self.config_path} "
                "doit contenir un dictionnaire YAML."
            )
        return _resolve_env(config)

    def section(self, name: str) -> dict[str, Any]:
        """Renvoie une section du YAML (dict vide si elle est absente)."""
        return self.data.get(name) or {}


@lru_cache(maxsize=1)
def get_config() -> Configuration:
    """Configuration partagée : le fichier n'est lu qu'une seule fois."""
    return Configuration()
