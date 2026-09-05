"""Fase 3: botón Ver (inline) y sello de copias controladas en los PDF —
pie "copia no controlada" en toda descarga y marca de agua cuando lo servido
no es la copia vigente."""

import io

from pypdf import PdfReader
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def _real_pdf(text="Contenido de la política") -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    pdf.drawString(72, 700, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() for page in reader.pages)


def _approve(client, headers, doc_id, version=1):
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/{version}/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _submit(client, headers, doc_id, version=1):
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/{version}/submit", headers=headers)
    assert resp.status_code == 200, resp.text


def test_pdf_download_carries_uncontrolled_copy_footer(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc = upload_document(headers, code="POL-301", content=_real_pdf()).json()
    _submit(client, headers, doc["id"])
    _approve(client, headers, doc["id"])

    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert resp.status_code == 200
    text = _pdf_text(resp.content)
    assert "Copia no controlada" in text
    assert "POL-301 v1" in text
    # La copia vigente no lleva marca de agua de estado.
    assert "OBSOLETO" not in text
    assert "BORRADOR" not in text
    # El contenido original sigue ahí.
    assert "Contenido de la pol" in text


def test_draft_and_obsolete_versions_are_watermarked(
    client, make_tenant, auth_headers, upload_document, upload_version
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc = upload_document(headers, code="POL-302", content=_real_pdf("v1")).json()

    # En borrador → BORRADOR.
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert "BORRADOR" in _pdf_text(resp.content)

    # Aprobada v1, luego v2 la vuelve obsoleta → OBSOLETO en v1.
    _submit(client, headers, doc["id"])
    _approve(client, headers, doc["id"])
    upload_version(headers, doc["id"], content=_real_pdf("v2"), filename="v2.pdf")
    _submit(client, headers, doc["id"], version=2)
    _approve(client, headers, doc["id"], version=2)

    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert "OBSOLETO" in _pdf_text(resp.content)
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/2/file", headers=headers)
    assert "OBSOLETO" not in _pdf_text(resp.content)


def test_retired_document_pdf_is_stamped_derogado(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc = upload_document(headers, code="POL-303", content=_real_pdf()).json()
    _submit(client, headers, doc["id"])
    _approve(client, headers, doc["id"])
    resp = client.post(
        f"/api/v1/documents/{doc['id']}/retire",
        json={"reason": "Reemplazada por la política nueva"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert "DEROGADO" in _pdf_text(resp.content)


def test_inline_param_serves_for_reading_in_browser(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc = upload_document(headers, code="POL-304", content=_real_pdf()).json()

    resp = client.get(
        f"/api/v1/documents/{doc['id']}/versions/1/file", params={"inline": "true"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].startswith("inline")
    assert resp.headers["content-type"] == "application/pdf"

    # Sin el parámetro sigue siendo descarga.
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert resp.headers["content-disposition"].startswith("attachment")


def test_unstampable_pdf_and_non_pdf_are_served_unchanged(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    # "PDF" con firma válida pero cuerpo no procesable: el sello no debe
    # romper la descarga — se sirve el original.
    fake_pdf = b"%PDF-1.4 contenido minimo sin estructura real"
    doc = upload_document(headers, code="POL-305", content=fake_pdf).json()
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert resp.status_code == 200
    assert resp.content == fake_pdf

    # Un archivo de texto no se estampa: bytes idénticos.
    txt = b"registro plano de evidencia"
    doc = upload_document(
        headers, code="REG-305", content=txt, filename="registro.txt", content_type="text/plain"
    ).json()
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=headers)
    assert resp.content == txt
