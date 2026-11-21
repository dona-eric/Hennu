"""
Système de gestion des prompts avec templates versionnés.
Support de variables, conditions et composition.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PromptTemplate:
    """Template de prompt versionné."""

    name: str
    version: str
    template: str
    description: str = ""
    variables: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def render(self, **kwargs) -> str:
        """
        Rend le template avec les variables fournies.

        Args:
            **kwargs: Variables à injecter dans le template

        Returns:
            Prompt rendu
        """
        # Vérifier les variables requises
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # Remplacer les variables
        rendered = self.template
        for var, value in kwargs.items():
            # Support de différents formats: {var}, {{var}}, $var
            rendered = rendered.replace(f"{{{var}}}", str(value))
            rendered = rendered.replace(f"{{{{{var}}}}}", str(value))
            rendered = rendered.replace(f"${var}", str(value))

        return rendered

    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire."""
        return {
            "name": self.name,
            "version": self.version,
            "template": self.template,
            "description": self.description,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptTemplate":
        """Crée depuis un dictionnaire."""
        return cls(**data)


class PromptManager:
    """
    Gestionnaire de prompts avec versioning.

    Permet de stocker, versionner et récupérer des templates de prompts.
    """

    def __init__(self):
        """Initialise le gestionnaire."""
        self.templates: dict[str, dict[str, PromptTemplate]] = {}
        # Structure: {name: {version: template}}

    def register_template(self, template: PromptTemplate, set_as_default: bool = True) -> None:
        """
        Enregistre un template.

        Args:
            template: Template à enregistrer
            set_as_default: Si True, devient la version par défaut
        """
        if template.name not in self.templates:
            self.templates[template.name] = {}

        self.templates[template.name][template.version] = template

        # Marquer comme version par défaut
        if set_as_default:
            self.templates[template.name]["default"] = template

    def get_template(self, name: str, version: str | None = None) -> PromptTemplate:
        """
        Récupère un template.

        Args:
            name: Nom du template
            version: Version spécifique (None = version par défaut)

        Returns:
            Template
        """
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")

        if version is None:
            version = "default"

        if version not in self.templates[name]:
            available = [v for v in self.templates[name].keys() if v != "default"]
            raise ValueError(
                f"Version '{version}' not found for template '{name}'. "
                f"Available versions: {available}"
            )

        return self.templates[name][version]

    def render_template(self, name: str, version: str | None = None, **kwargs) -> str:
        """
        Récupère et rend un template.

        Args:
            name: Nom du template
            version: Version spécifique
            **kwargs: Variables pour le rendu

        Returns:
            Prompt rendu
        """
        template = self.get_template(name, version)
        return template.render(**kwargs)

    def list_templates(self) -> list[dict[str, Any]]:
        """
        Liste tous les templates disponibles.

        Returns:
            Liste de métadonnées des templates
        """
        result = []
        for name, versions in self.templates.items():
            for version, template in versions.items():
                if version == "default":
                    continue
                result.append(
                    {
                        "name": name,
                        "version": version,
                        "description": template.description,
                        "variables": template.variables,
                        "is_default": template == versions.get("default"),
                    }
                )
        return result

    def export_templates(self, filepath: str) -> None:
        """
        Exporte tous les templates vers un fichier JSON.

        Args:
            filepath: Chemin du fichier de sortie
        """
        data = {}
        for name, versions in self.templates.items():
            data[name] = {}
            for version, template in versions.items():
                if version == "default":
                    continue
                data[name][version] = template.to_dict()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_templates(self, filepath: str) -> None:
        """
        Importe des templates depuis un fichier JSON.

        Args:
            filepath: Chemin du fichier à importer
        """
        with open(filepath) as f:
            data = json.load(f)

        for _name, versions in data.items():
            for _version, template_dict in versions.items():
                template = PromptTemplate.from_dict(template_dict)
                self.register_template(template, set_as_default=False)


# Templates RAG prédéfinis
RAG_SYSTEM_PROMPT = PromptTemplate(
    name="rag_agentic_system_prompt",
    version="1.0",
    template="""Tu es un assistant IA spécialisé en douane qui répond aux questions en français en te basant sur le contexte fourni.

    RÈGLES IMPORTANTES :
    1. Réponds TOUJOURS en français, quelle que soit la langue de la question.
    2. Utilise EN PRIORITÉ les informations du contexte ci-dessous pour répondre.
    3. Si le contexte ne contient pas suffisamment d'informations pour répondre précisément :
    - Indique d'abord : "Je n'ai pas trouvé d'informations précises dans la base de données sur ce sujet."
    - Puis donne quand même une réponse générale en commençant par : "Je pense que..."
    4. Ne cite pas de sources inexistantes.
    5. Sois concis et précis.
    6. ALWAYS cite your sources using [1], [2], etc. after each claim
    7. Distinguish clearly between what is stated in the context vs your interpretation
    8. If context is insufficient, say so in the user's language



    Contexte extrait de la base de données :
    {context}""",
        description="System prompt pour RAG Agentic (français)",
        variables=["context"],
)


# Version 1.0.1 : même structure que la 1.0 (contexte dans le prompt
# système, citations [1], [2]...), mais sans réponse « au jugé » :
# en droit douanier, Hɛnnu ne répond qu'à partir des textes fournis.
RAG_SYSTEM_PROMPT_V101 = PromptTemplate(
    name="rag_agentic_system_prompt",
    version="1.0.1",
    template="""Tu es Hɛnnu, un assistant expert de la réglementation douanière
béninoise (Code des Douanes du Bénin, Port Autonome de Cotonou, Douanes Béninoises).
Tu t'adresses à des commissionnaires en douane agréés et à des professionnels exigeants.

RÈGLES IMPORTANTES :
1. Réponds TOUJOURS en français, quelle que soit la langue de la question.
2. Réponds UNIQUEMENT à partir des extraits du contexte ci-dessous.
3. Si le contexte ne permet pas de répondre avec certitude, dis-le clairement :
   "Je n'ai pas trouvé d'informations précises dans les textes disponibles
   sur ce sujet."
   N'invente jamais de règle, de taux, de délai ou de numéro d'article.
4. Cite tes sources après chaque affirmation importante avec leur numéro [1], [2]...
   en précisant le numéro d'article quand il est connu.
5. Ne cite jamais une source absente du contexte.
6. Distingue clairement ce que disent les textes de ton interprétation.
7. Le texte de référence est le Code des Douanes en vigueur (loi n° 2014-20 du
   12 septembre 2014, version modifiée). Base ta réponse d'abord sur lui. Cite les
   autres versions (version initiale, ancien code de 1966) seulement en complément,
   en précisant clairement qu'il s'agit d'un texte antérieur.
8. Adopte un ton professionnel, clair et juridiquement rigoureux.

Contexte extrait de la base documentaire :
{context}""",
    description="System prompt Hɛnnu : réponses sourcées, sans invention",
    variables=["context"],
)


QUERY_REWRITE_PROMPT = PromptTemplate(
    name="rag_query_rewrite",
    version="1.0.1",
    template="""Tu es un expert de la législation douanière béninoise.
Reformule la question ci-dessous pour optimiser la recherche dans une base
documentaire juridique (Code des Douanes du Bénin, manuels de procédures).

Règles :
- Conserve le sens exact de la question.
- Utilise le vocabulaire juridique et douanier approprié.
- N'ajoute aucune information absente de la question.
- Retourne uniquement la question reformulée, sans commentaire.

Question : {question}""",
    description="Reformulation de la question avant la recherche",
    variables=["question"],
)


def create_default_prompt_manager() -> PromptManager:
    """
    Crée un gestionnaire de prompts avec les templates par défaut.

    Returns:
        PromptManager avec templates prédéfinis
    """
    manager = PromptManager()

    # Enregistrer tous les templates par défaut
    # (le dernier enregistré d'un même nom devient sa version par défaut)
    default_templates = (
        RAG_SYSTEM_PROMPT,
        RAG_SYSTEM_PROMPT_V101,
        QUERY_REWRITE_PROMPT,
    )

    for template in default_templates:
        manager.register_template(template)

    return manager
