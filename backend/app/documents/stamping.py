"""Sello de copias controladas al servir PDFs (Fase 3).

ISO 27001 cl. 7.5.3.d exige prevenir el uso de información obsoleta: hoy un
PDF obsoleto descargado ayer es indistinguible del vigente. Este módulo
estampa, en el momento de servir:

- un **pie de página** en todas las páginas — "Copia no controlada · CÓDIGO
  vN · descargada el FECHA por USUARIO": toda copia fuera de la plataforma
  es, por definición, no controlada (la controlada es la que vive aquí);
- una **marca de agua diagonal** cuando la versión servida NO es la copia
  vigente (BORRADOR, EN REVISIÓN, OBSOLETO) o el documento entero está
  DEROGADO.

Solo aplica a PDFs — otros formatos (Office, imágenes) se sirven tal cual.
El estampado es defensa documental, no frontera de seguridad: si un PDF no
se puede procesar (corrupto, cifrado, versiones pre-plataforma con
contenido de prueba), se sirve el original en vez de romper la descarga.
"""

import io
import logging

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

_FOOTER_MARGIN_PTS = 18
_FOOTER_FONT = ("Helvetica", 7.5)
_WATERMARK_FONT = ("Helvetica-Bold", 72)
_WATERMARK_COLOR = Color(0.75, 0.16, 0.12, alpha=0.16)
_FOOTER_COLOR = Color(0.35, 0.35, 0.35)


def _overlay_page(width: float, height: float, footer_text: str, watermark: str | None) -> bytes:
    """Genera un PDF de una página (del mismo tamaño) con el pie y la marca."""
    buffer = io.BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(width, height))

    overlay.setFont(*_FOOTER_FONT)
    overlay.setFillColor(_FOOTER_COLOR)
    overlay.drawCentredString(width / 2, _FOOTER_MARGIN_PTS, footer_text)

    if watermark:
        overlay.saveState()
        overlay.translate(width / 2, height / 2)
        overlay.rotate(45)
        overlay.setFont(*_WATERMARK_FONT)
        overlay.setFillColor(_WATERMARK_COLOR)
        overlay.drawCentredString(0, 0, watermark)
        overlay.restoreState()

    overlay.showPage()
    overlay.save()
    return buffer.getvalue()


def stamp_pdf(content: bytes, *, footer_text: str, watermark: str | None) -> bytes:
    """Devuelve el PDF con pie (y marca de agua si aplica) en cada página.

    Si el contenido no es un PDF procesable, devuelve el original sin tocar
    — nunca rompe una descarga por culpa del sello.
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            return content
        writer = PdfWriter()
        # Un overlay por tamaño de página distinto (la mayoría de PDFs usan
        # uno solo) — se cachea para no regenerarlo página a página.
        overlays: dict[tuple[float, float], object] = {}
        for page in reader.pages:
            box = page.mediabox
            size = (float(box.width), float(box.height))
            if size not in overlays:
                overlay_bytes = _overlay_page(size[0], size[1], footer_text, watermark)
                overlays[size] = PdfReader(io.BytesIO(overlay_bytes)).pages[0]
            page.merge_page(overlays[size])  # type: ignore[arg-type]
            writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception:  # noqa: BLE001 - cualquier PDF raro se sirve sin sello
        logger.warning("No se pudo estampar el PDF; se sirve el original", exc_info=True)
        return content
