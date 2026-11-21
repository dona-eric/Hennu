"""Fragments HTML de l'interface.

Ces fonctions ne produisent que de la structure (balises + classes) :
toute la mise en forme est dans static/css. Les textes venant de
l'utilisateur ou des documents sont systématiquement échappés.
"""

from html import escape


def brand(name: str, tagline: str) -> str:
    return (
        '<div class="hn-brand">'
        '<span class="hn-brand__mark">⚖</span>'
        "<div>"
        f'<div class="hn-brand__name">{escape(name)}</div>'
        f'<div class="hn-brand__tagline">{escape(tagline)}</div>'
        "</div></div>"
    )


def status_pill(label: str) -> str:
    return (
        '<div class="hn-status">'
        '<span class="hn-status__dot"></span>'
        f"{escape(label)}</div>"
    )


def section_label(text: str) -> str:
    return f'<div class="hn-section-label">{escape(text)}</div>'


def icon(name: str) -> str:
    """Icône Material Symbols (ex. « search », « verified »)."""
    return f'<span class="hn-icon" aria-hidden="true">{escape(name)}</span>'


# ------------------------------------------------------------------
# Page d'accueil
# ------------------------------------------------------------------

def nav_brand(name: str) -> str:
    return (
        '<div class="hn-nav-brand">'
        '<span class="hn-nav-brand__mark">⚖</span>'
        f"{escape(name)}</div>"
    )


def hero(name: str, organisation: str, tagline: str, text: str) -> str:
    return (
        '<header class="hn-hero">'
        '<div class="hn-hero__glow"></div>'
        f'<p class="hn-hero__eyebrow">{escape(organisation)}</p>'
        f'<h1 class="hn-hero__title">{escape(name)}</h1>'
        '<span class="hn-hero__rule"></span>'
        f'<p class="hn-hero__tagline">{escape(tagline)}</p>'
        f'<p class="hn-hero__text">{escape(text)}</p>'
        "</header>"
    )


def section_heading(eyebrow: str, title: str) -> str:
    return (
        '<div class="hn-heading">'
        f'<span class="hn-heading__eyebrow">{escape(eyebrow)}</span>'
        f"<h2>{escape(title)}</h2>"
        "</div>"
    )


def features(items: tuple[tuple[str, str, str], ...]) -> str:
    """Grille « Ce que fait Hɛnnu » : (icône, titre, texte)."""
    cards = "".join(
        '<div class="hn-feature">'
        f'<div class="hn-feature__icon">{icon(name)}</div>'
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(text)}</p>"
        "</div>"
        for name, title, text in items
    )
    return f'<div class="hn-features">{cards}</div>'


def how_it_works(items: tuple[tuple[str, str], ...]) -> str:
    """Étapes numérotées « Comment ça marche » : (titre, texte)."""
    steps_html = "".join(
        '<li class="hn-how__step">'
        f'<span class="hn-how__number">{index}</span>'
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(text)}</p>"
        "</li>"
        for index, (title, text) in enumerate(items, start=1)
    )
    return f'<ol class="hn-how">{steps_html}</ol>'


def module_card(icon_name: str, title: str, text: str, badge: str) -> str:
    """Carte d'un module de Hɛnnu (assistant, audit, base documentaire)."""
    return (
        '<div class="hn-card">'
        '<div class="hn-card__top">'
        f'<div class="hn-card__icon">{icon(icon_name)}</div>'
        f'<span class="hn-card__badge">{escape(badge)}</span>'
        "</div>"
        f'<h3 class="hn-card__title">{escape(title)}</h3>'
        f'<p class="hn-card__text">{escape(text)}</p>'
        "</div>"
    )


# ------------------------------------------------------------------
# Assistant
# ------------------------------------------------------------------

def empty_state(title: str, text: str) -> str:
    return (
        '<div class="hn-empty">'
        '<span class="hn-empty__mark">⚖</span>'
        f"<h2>{escape(title)}</h2>"
        f"<p>{escape(text)}</p>"
        "</div>"
    )


def chat_header(title: str, subtitle: str) -> str:
    return (
        '<div class="hn-chat-header">'
        '<span class="hn-chat-header__mark">⚖</span>'
        "<div>"
        f'<div class="hn-chat-header__title">{escape(title)}</div>'
        f'<div class="hn-chat-header__subtitle">{escape(subtitle)}</div>'
        "</div></div>"
    )


def steps(items: list[tuple[str, str, str]]) -> str:
    """Frise de progression de l'agent.

    `items` contient des triplets (libellé, détail, état) où l'état vaut
    « done », « active » ou « pending ».
    """
    rows = []
    for label, detail, state in items:
        detail_html = ""
        if detail:
            detail_html = f'<div class="hn-step__detail">{escape(detail)}</div>'
        rows.append(
            f'<li class="hn-step is-{state}">'
            '<span class="hn-step__dot"></span>'
            "<div>"
            f'<div class="hn-step__label">{escape(label)}</div>'
            f"{detail_html}"
            "</div></li>"
        )
    return f'<ol class="hn-steps">{"".join(rows)}</ol>'


def source_stamps(sources: list[dict]) -> str:
    """Rangée de « tampons » citant les articles utilisés."""
    stamps = []
    for index, source in enumerate(sources, start=1):
        article = source.get("article") or f"Source {index}"
        document = source.get("title") or article
        stamps.append(
            f'<span class="hn-stamp" title="{escape(document)}">'
            f'<span class="hn-stamp__index">{index}</span>'
            f"{escape(article)}</span>"
        )
    return f'<div class="hn-stamps">{"".join(stamps)}</div>'


def message_meta(parts: list[str]) -> str:
    text = " · ".join(escape(part) for part in parts if part)
    return f'<div class="hn-meta">{text}</div>'


def reasoning_note(label: str, text: str) -> str:
    return (
        '<div class="hn-reasoning">'
        f'<span class="hn-reasoning__label">{escape(label)}</span>'
        f"{escape(text)}</div>"
    )


def excerpt(index: int, title: str, content: str) -> str:
    """Extrait d'un texte source, affiché dans le panneau des sources."""
    title = title or f"Source {index}"
    return (
        '<article class="hn-excerpt">'
        '<div class="hn-excerpt__title">'
        f'<span class="hn-stamp__index">{index}</span>{escape(title)}</div>'
        f'<div class="hn-excerpt__body">{escape(content)}</div>'
        "</article>"
    )


def footer(name: str, year: int) -> str:
    return (
        '<footer class="hn-footer">'
        f'<span class="hn-footer__brand">{escape(name)}</span>'
        f"<span>© {year} {escape(name)} — Tous droits réservés.</span>"
        "</footer>"
    )
