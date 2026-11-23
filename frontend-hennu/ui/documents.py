"""Page « Base documentaire » : bibliothèque, liseuse, proposition, administration.

Les documents se lisent page par page (images) : le fichier original
n'est jamais envoyé au navigateur et aucun bouton de téléchargement
n'est proposé.
"""

import streamlit as st

from service import documents as docs_service
from service.backend import library
from settings import (
    APP_NAME,
    COPYRIGHT_YEAR,
    DOCUMENT_STATUS_LABELS,
    STATUS_REFRESH_SECONDS,
    UPLOAD_MAX_MB,
)
from ui import templates
from ui.navbar import render_navbar


def render_documents_page() -> None:
    docs_service.ensure_library_ready()
    render_navbar()

    document_id = st.query_params.get("doc")
    if document_id:
        _render_reader(document_id)
    else:
        _render_index()

    st.html(templates.footer(APP_NAME, COPYRIGHT_YEAR))


def _render_index() -> None:
    published = library.published_documents()
    pages = sum(document.page_count or 0 for document in published)
    st.html(
        templates.documents_header(
            "Base documentaire",
            "Les textes douaniers sur lesquels s'appuie Orion, "
            "consultables directement en ligne.",
            stats=[
                (str(len(published)), "documents publiés"),
                (f"{pages:,}".replace(",", " "), "pages consultables"),
            ],
        )
    )

    library_tab, submit_tab, admin_tab = st.tabs(
        ["Bibliothèque", "Proposer un document", "Administration"]
    )
    with library_tab:
        _render_library(published)
    with submit_tab:
        _render_submit_form()
    with admin_tab:
        _render_admin()


# ------------------------------------------------------------------
# Bibliothèque publique
# ------------------------------------------------------------------

def _render_library(published: list) -> None:
    search = st.text_input(
        "Rechercher un document",
        placeholder="Rechercher par titre ou mot-clé…",
        key="library_search",
        label_visibility="collapsed",
        icon=":material/search:",
    )
    documents = [doc for doc in published if _matches(doc, search)]

    if not documents:
        st.html(templates.empty_note("Aucun document ne correspond à votre recherche."))
        return

    columns = st.columns(3, gap="medium")
    for index, document in enumerate(documents):
        with columns[index % 3], st.container(key=f"doc_card_{document.id}"):
            st.html(
                templates.document_card(
                    title=document.title,
                    description=document.description,
                    file_type=document.file_type,
                    meta=_document_meta(document),
                )
            )
            st.button(
                "Lire le document",
                key=f"read_{document.id}",
                icon=":material/menu_book:",
                width="stretch",
                on_click=_open_reader,
                args=(document.id,),
            )


def _matches(document, search: str) -> bool:
    words = search.lower().split()
    haystack = f"{document.title} {document.description}".lower()
    return all(word in haystack for word in words)


def _document_meta(document) -> list[str]:
    parts = [document.file_type.upper()]
    if document.page_count:
        plural = "s" if document.page_count > 1 else ""
        parts.append(f"{document.page_count} page{plural}")
    if document.uploaded_by:
        parts.append(f"Ajouté par {document.uploaded_by}")
    return parts


# ------------------------------------------------------------------
# Liseuse (pages en images, sans téléchargement)
# ------------------------------------------------------------------

def _open_reader(document_id: str) -> None:
    st.query_params.from_dict({"doc": document_id, "page": "1"})


def _close_reader() -> None:
    st.query_params.clear()


def _go_to_page(page: int, input_key: str) -> None:
    st.query_params["page"] = str(page)
    st.session_state[input_key] = page


def _on_page_input(input_key: str) -> None:
    st.query_params["page"] = str(st.session_state[input_key])


def _render_reader(document_id: str) -> None:
    st.button(
        "Retour à la bibliothèque",
        key="reader_back",
        icon=":material/arrow_back:",
        type="tertiary",
        on_click=_close_reader,
    )

    document = library.get_document(document_id)
    # Un document non publié n'est visible que par un administrateur
    if document is None or not (document.is_ready or docs_service.is_admin()):
        st.warning("Ce document est introuvable ou n'est pas encore publié.")
        return

    with st.spinner("Préparation de l'aperçu…"):
        total = library.page_count(document)

    st.html(
        templates.reader_header(
            document.title,
            document.description,
            _document_meta(document),
        )
    )
    if total == 0:
        st.info("L'aperçu de ce document n'est pas disponible pour le moment.")
        return

    page = _current_page(total)
    input_key = f"page_input_{document.id}"
    st.session_state.setdefault(input_key, page)

    with st.container(
        key="reader_toolbar",
        horizontal=True,
        vertical_alignment="center",
        horizontal_alignment="center",
    ):
        st.button(
            "Précédente",
            key="reader_previous",
            icon=":material/chevron_left:",
            disabled=page <= 1,
            on_click=_go_to_page,
            args=(page - 1, input_key),
        )
        st.number_input(
            "Page",
            min_value=1,
            max_value=total,
            step=1,
            key=input_key,
            on_change=_on_page_input,
            args=(input_key,),
            label_visibility="collapsed",
            width=110,
        )
        st.html(f'<span class="hn-reader__total">/ {total}</span>', width="content")
        st.button(
            "Suivante",
            key="reader_next",
            icon=":material/chevron_right:",
            icon_position="right",
            disabled=page >= total,
            on_click=_go_to_page,
            args=(page + 1, input_key),
        )

    image = docs_service.page_image(document.id, page, str(document.updated_at))
    with st.container(key="reader_page"):
        if image is None:
            st.info("Cette page n'a pas pu être affichée.")
        else:
            st.image(image, width="stretch")


def _current_page(total: int) -> int:
    try:
        page = int(st.query_params.get("page", 1))
    except ValueError:
        page = 1
    return min(max(page, 1), total)


# ------------------------------------------------------------------
# Proposer un document
# ------------------------------------------------------------------

def _render_submit_form() -> None:
    st.html(
        templates.form_intro(
            "Proposer un document",
            "Votre document sera examiné par un administrateur. Une fois "
            "validé, il sera publié dans la bibliothèque et utilisé par "
            "l'assistant pour répondre aux questions.",
        )
    )

    with st.form("submit_document", clear_on_submit=True, border=False):
        uploaded = st.file_uploader(
            f"Document (PDF ou DOCX, {UPLOAD_MAX_MB} Mo maximum)",
            type=["pdf", "docx"],
        )
        title = st.text_input("Titre du document *", max_chars=300)
        description = st.text_area(
            "Description (facultatif)",
            max_chars=1000,
            height=90,
            placeholder="Nature du texte, date, service émetteur…",
        )
        author = st.text_input("Votre nom ou organisme (facultatif)", max_chars=120)
        submitted = st.form_submit_button(
            "Envoyer pour validation",
            type="primary",
            icon=":material/upload:",
        )

    if not submitted:
        return
    if uploaded is None or not title.strip():
        st.error("Ajoutez un fichier et un titre avant d'envoyer.")
        return

    try:
        library.submit_document(
            filename=uploaded.name,
            content=uploaded.getvalue(),
            title=title,
            description=description,
            uploaded_by=author,
        )
    except ValueError as error:
        st.error(str(error))
        return

    st.success(
        "Merci ! Votre document a bien été reçu. Il sera publié après validation.",
        icon=":material/check_circle:",
    )


# ------------------------------------------------------------------
# Administration
# ------------------------------------------------------------------

def _render_admin() -> None:
    if not docs_service.admin_enabled():
        st.info(
            "L'administration est désactivée. Ajoutez la variable "
            "`HENNU_ADMIN_PASSWORD` dans le fichier `.env` pour l'activer.",
            icon=":material/lock:",
        )
        return

    if not docs_service.is_admin():
        _render_login()
        return

    with st.container(horizontal=True, vertical_alignment="center"):
        st.html(templates.section_label("Espace administrateur"), width="content")
        st.space("stretch")
        st.button(
            "Se déconnecter",
            key="admin_logout",
            icon=":material/logout:",
            type="tertiary",
            on_click=docs_service.logout,
        )

    # Rafraîchissement automatique tant qu'une ingestion est en cours
    refresh = STATUS_REFRESH_SECONDS if library.is_busy() else None
    st.fragment(_render_admin_lists, run_every=refresh)()


def _render_login() -> None:
    with st.form("admin_login", border=False, width=420):
        password = st.text_input("Mot de passe administrateur", type="password")
        submitted = st.form_submit_button("Se connecter", icon=":material/login:")

    if submitted:
        if docs_service.login(password):
            st.rerun()
        st.error("Mot de passe incorrect.")


def _render_admin_lists() -> None:
    documents = library.all_documents()
    groups = (
        ("À valider", ("pending",)),
        ("En cours", ("approved", "processing")),
        ("Échecs", ("failed",)),
        ("Publiés", ("ready",)),
        ("Refusés et retirés", ("rejected",)),
    )

    for label, statuses in groups:
        group = [doc for doc in documents if doc.status in statuses]
        st.html(templates.section_label(f"{label} ({len(group)})"))
        if not group:
            st.caption("Aucun document.")
        for document in group:
            _render_admin_item(document)


def _render_admin_item(document) -> None:
    with st.container(key=f"admin_{document.id}"):
        st.html(
            templates.admin_item(
                title=document.title,
                description=document.description,
                meta=_admin_meta(document),
                status=document.status,
                status_label=DOCUMENT_STATUS_LABELS.get(
                    document.status, document.status
                ),
                message=document.status_message,
            )
        )
        with st.container(horizontal=True, gap="small"):
            _admin_actions(document)


def _admin_meta(document) -> list[str]:
    parts = [document.original_name, f"{document.size_bytes / 1_048_576:.1f} Mo"]
    parts.append(f"priorité {document.priority}")
    if document.chunk_count:
        parts.append(f"{document.chunk_count} passages indexés")
    if document.uploaded_by:
        parts.append(f"par {document.uploaded_by}")
    parts.append(document.created_at.strftime("%d/%m/%Y %H:%M"))
    return parts


def _admin_actions(document) -> None:
    """Boutons d'action selon le statut du document."""
    key = document.id
    status = document.status

    if status in ("pending", "failed", "ready"):
        st.button(
            "Aperçu",
            key=f"preview_{key}",
            icon=":material/visibility:",
            on_click=_open_reader,
            args=(key,),
        )

    if status == "pending":
        if st.button("Valider", key=f"approve_{key}", type="primary",
                     icon=":material/check:"):
            library.approve_document(key)
            st.rerun(scope="app")
        with st.popover("Refuser", icon=":material/close:"):
            reason = st.text_input("Motif (facultatif)", key=f"reason_{key}")
            if st.button("Confirmer le refus", key=f"reject_{key}"):
                library.reject_document(key, reason)
                st.rerun(scope="app")

    if status == "failed":
        if st.button("Relancer", key=f"retry_{key}", type="primary",
                     icon=":material/refresh:"):
            library.retry_document(key)
            st.rerun(scope="app")

    if status == "ready":
        with st.popover("Modifier", icon=":material/edit:"):
            title = st.text_input("Titre", value=document.title, key=f"title_{key}")
            priority = st.number_input(
                "Priorité (1 = texte de référence)",
                min_value=1,
                max_value=9,
                value=document.priority,
                key=f"priority_{key}",
            )
            st.caption("Enregistrer ré-indexe le document.")
            if st.button("Enregistrer", key=f"save_{key}", type="primary"):
                library.update_details(key, title, int(priority))
                st.rerun(scope="app")

    if status in ("ready", "failed"):
        with st.popover("Retirer", icon=":material/delete:"):
            st.warning("Le document ne sera plus utilisé par l'assistant ni publié.")
            if st.button("Confirmer le retrait", key=f"remove_{key}"):
                library.remove_document(key)
                st.rerun(scope="app")
