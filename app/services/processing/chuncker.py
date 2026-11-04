from dataclasses import dataclass, field
import re
from uuid import uuid4
from app.core.loger import setup_logging
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode

"""
Ici je teste dans un premier temps la technique de segmentation Hierachique
car les données sont des rapports, des articles avec des sections, des codes et lois.
"""
logger = setup_logging()

CHUNK_SIZE = 384
CHUNK_OVERLAP = 50

@dataclass
class LegalBlock:
    block_type: str
    title: str
    text: str = ""
    metadata: dict = field(default_factory=dict)


def clean_markdown_line(line: str) -> str:
    """Nettoie les caractères Markdown autour des titres."""
    line = re.sub(r"^\s*#{1,6}\s*", "", line)
    line = re.sub(r"\*{1,2}", "", line)
    line = re.sub(r"\\([.*])", r"\1", line)
    return line.strip()


def detect_structure(line: str):
    """Détecte la structure juridique indépendamment du nombre de # dans le Markdown."""
    line = clean_markdown_line(line)

    patterns = [
        ("CHAPTER", r"^Chapitre\s+([IVXLCDM]+)\b\s*(.*)$"),
        ("SECTION", r"^Section\s+([IVXLCDM]+)\s*[:.\-]?\s*(.*)$"),
        ("SUBSECTION", r"^\d+\.\s+(.+)$"),
        ("ARTICLE", r"^Article\s+(\d+[A-Za-z]?)\b\s*(.*)$"),
    ]

    for block_type, pattern in patterns:
        match = re.match(pattern, line, flags=re.IGNORECASE)
        if match:
            return block_type, match.groups()

    return None, None


def parse_legal_document(markdown: str) -> list[LegalBlock]:
    lines = markdown.splitlines()
    blocks = []

    context = {
        "chapter": None,
        "section": None,
        "subsection": None,
    }

    current_article = None
    article_lines = []

    def flush_article():
        nonlocal current_article, article_lines
        if current_article is None:
            return

        article_text = "\n".join(article_lines).strip()
        if article_text:
            blocks.append(
                LegalBlock(
                    block_type="ARTICLE",
                    title=current_article["title"],
                    text=article_text,
                    metadata={
                        **context,
                        "article_number": current_article["number"],
                    },
                )
            )

        current_article = None
        article_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Nettoyage des artefacts de pagination
        if re.fullmatch(r"\{\d+\}[-\s]*", line):
            continue

        if line.lower().startswith("code des douanes de la république du bénin"):
            continue

        block_type, groups = detect_structure(line)

        if block_type == "CHAPTER":
            flush_article()
            number, title = groups
            context = {
                "chapter": f"Chapitre {number} {title}".strip(),
                "section": None,
                "subsection": None,
            }

        elif block_type == "SECTION":
            flush_article()
            number, title = groups
            context["section"] = f"Section {number} {title}".strip()
            context["subsection"] = None

        elif block_type == "SUBSECTION":
            flush_article()
            title = groups[0]
            context["subsection"] = title

        elif block_type == "ARTICLE":
            flush_article()
            number, title = groups
            current_article = {
                "number": number,
                "title": f"Article {number}",
            }

        elif current_article is not None:
            article_lines.append(raw_line)

    flush_article()
    return blocks


def create_node(text: str, node_type: str, metadata: dict) -> TextNode:
    return TextNode(
        id_=str(uuid4()),
        text=text,
        metadata={**metadata, "node_type": node_type},
    )


def link_parent_child(parent: TextNode, child: TextNode):
    """Crée les relations parent-enfant."""
    child.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
        node_id=parent.node_id
    )

    children = parent.relationships.get(NodeRelationship.CHILD, [])
    children.append(RelatedNodeInfo(node_id=child.node_id))
    parent.relationships[NodeRelationship.CHILD] = children


def build_legal_hierarchy(blocks: list[LegalBlock]):
    """Construit la hiérarchie juridique complète."""
    all_nodes = []
    leaf_nodes = []
    structural_nodes = {}

    splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    for block in blocks:
        metadata = block.metadata
        chapter = metadata.get("chapter")
        section = metadata.get("section")
        subsection = metadata.get("subsection")

        parent = None

        # Chapitre
        if chapter:
            chapter_key = ("chapter", chapter)
            if chapter_key not in structural_nodes:
                chapter_node = create_node(
                    text=chapter,
                    node_type="CHAPTER",
                    metadata={"chapter": chapter},
                )
                structural_nodes[chapter_key] = chapter_node
                all_nodes.append(chapter_node)
            parent = structural_nodes[chapter_key]

        # Section
        if section:
            section_key = ("section", chapter, section)
            if section_key not in structural_nodes:
                section_node = create_node(
                    text=section,
                    node_type="SECTION",
                    metadata={"chapter": chapter, "section": section},
                )
                structural_nodes[section_key] = section_node
                if parent is not None:
                    link_parent_child(parent, section_node)
                all_nodes.append(section_node)
            parent = structural_nodes[section_key]

        # Sous-section
        if subsection:
            subsection_key = ("subsection", chapter, section, subsection)
            if subsection_key not in structural_nodes:
                subsection_node = create_node(
                    text=subsection,
                    node_type="SUBSECTION",
                    metadata={
                        "chapter": chapter,
                        "section": section,
                        "subsection": subsection,
                    },
                )
                structural_nodes[subsection_key] = subsection_node
                if parent is not None:
                    link_parent_child(parent, subsection_node)
                all_nodes.append(subsection_node)
            parent = structural_nodes[subsection_key]

        # Article
        article_node = create_node(
            text=block.title + "\n\n" + block.text,
            node_type="ARTICLE",
            metadata=metadata,
        )

        if parent is not None:
            link_parent_child(parent, article_node)

        all_nodes.append(article_node)

        # Segmentation de l'article en chunks
        chunks = splitter.split_text(block.text)
        for chunk_index, chunk_text in enumerate(chunks):
            chunk_node = create_node(
                text=chunk_text,
                node_type="CHUNK",
                metadata={
                    **metadata,
                    "article_title": block.title,
                    "chunk_index": chunk_index,
                },
            )
            link_parent_child(article_node, chunk_node)
            all_nodes.append(chunk_node)
            leaf_nodes.append(chunk_node)

    return all_nodes, leaf_nodes


def chunk_documents(markdown: str):
    """Pipeline complet : Markdown -> blocs juridiques -> hiérarchie."""
    blocks = parse_legal_document(markdown)
    all_nodes, leaf_nodes = build_legal_hierarchy(blocks)
    return all_nodes, leaf_nodes