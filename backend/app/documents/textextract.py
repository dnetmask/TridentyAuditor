"""Extracción de texto para la búsqueda de contenido (Fase 5b).

Se corre una vez, al subir cada versión: el texto se guarda en
``DocumentVersion.content_text`` y Postgres mantiene el ``tsvector`` (columna
generada + índice GIN). Buscar es entonces una consulta indexada, no re-leer
binarios.

Es best-effort: si un archivo no se puede parsear (binario raro, PDF
escaneado sin capa de texto, formato no soportado), se guarda ``None`` y el
documento simplemente no aparece en la búsqueda por contenido — nunca rompe
la subida.
"""

import io
import logging

logger = logging.getLogger(__name__)

# Tope de caracteres indexados por versión — un tsvector gigante no aporta a
# la búsqueda y sí infla la fila. 1 MB de texto es más que suficiente.
_MAX_CHARS = 1_000_000


def extract_text(content: bytes, *, media_type: str | None, filename: str | None) -> str | None:
    """Devuelve el texto plano de un binario, o ``None`` si no se puede."""
    kind = _resolve_kind(media_type, filename)
    try:
        if kind == "pdf":
            text = _from_pdf(content)
        elif kind == "docx":
            text = _from_docx(content)
        elif kind == "text":
            text = content.decode("utf-8", errors="ignore")
        else:
            return None
    except Exception:  # noqa: BLE001 - cualquier archivo raro se indexa como vacío
        logger.warning("No se pudo extraer texto (%s); se omite del índice", kind, exc_info=True)
        return None
    text = (text or "").strip()
    if not text:
        return None
    return text[:_MAX_CHARS]


def _resolve_kind(media_type: str | None, filename: str | None) -> str | None:
    mt = (media_type or "").lower()
    name = (filename or "").lower()
    if mt == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if (
        mt == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or name.endswith(".docx")
    ):
        return "docx"
    if mt.startswith("text/") or name.endswith((".txt", ".md", ".csv")):
        return "text"
    return None


def _from_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        return ""
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _from_docx(content: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs)
