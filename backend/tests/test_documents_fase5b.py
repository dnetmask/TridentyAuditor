"""Fase 5b: búsqueda de texto completo y plantillas de documentos."""

import io

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def _pdf_with(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    pdf.drawString(72, 720, text)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


# ------------------------------------------------------- búsqueda full-text

def test_search_finds_by_content_not_metadata(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    # El texto buscado va SOLO en el contenido, no en código ni título.
    upload_document(
        headers,
        code="POL-600",
        title="Documento genérico",
        content=_pdf_with("El plan de continuidad del negocio se activa ante un ciberataque"),
    )
    upload_document(
        headers, code="POL-601", title="Otro documento", content=_pdf_with("Contenido sin relación")
    )

    hits = client.get("/api/v1/documents/search", params={"q": "continuidad negocio"}, headers=headers).json()
    codes = [d["code"] for d in hits]
    assert "POL-600" in codes
    assert "POL-601" not in codes

    # Búsqueda vacía → sin resultados, no error.
    assert client.get("/api/v1/documents/search", params={"q": "   "}, headers=headers).json() == []


def test_search_excludes_retired_documents(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc = upload_document(
        headers, code="POL-602", content=_pdf_with("término exclusivo criptografía cuántica")
    ).json()
    assert client.get(
        "/api/v1/documents/search", params={"q": "criptografía cuántica"}, headers=headers
    ).json()

    client.post(
        f"/api/v1/documents/{doc['id']}/retire", json={"reason": "obsoleto"}, headers=headers
    )
    assert client.get(
        "/api/v1/documents/search", params={"q": "criptografía cuántica"}, headers=headers
    ).json() == []


def test_search_isolated_per_tenant(client, make_tenant, auth_headers, upload_document):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    upload_document(
        auth_headers(tenant_a["id"]),
        code="POL-603",
        content=_pdf_with("frase secreta del tenant alfa"),
    )
    assert client.get(
        "/api/v1/documents/search", params={"q": "frase secreta alfa"}, headers=auth_headers(tenant_b["id"])
    ).json() == []


# ------------------------------------------------------------- plantillas

def _upload_template(client, headers, name="Plantilla de política"):
    return client.post(
        "/api/v1/documents/templates",
        data={"name": name, "document_type": "policy"},
        files={"file": ("plantilla.pdf", _pdf_with("Encabezado estándar del SGSI"), "application/pdf")},
        headers=headers,
    )


def test_template_crud_and_role_guard(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    viewer = auth_headers(tenant["id"], role="viewer")

    resp = _upload_template(client, admin)
    assert resp.status_code == 201, resp.text
    template = resp.json()

    # Duplicado por nombre → 409.
    assert _upload_template(client, admin).status_code == 409
    # Lee cualquiera; sube/borra solo can_write.
    assert client.get("/api/v1/documents/templates", headers=viewer).status_code == 200
    assert _upload_template(client, viewer, name="X").status_code == 403

    # Descargar el archivo de la plantilla.
    dl = client.get(f"/api/v1/documents/templates/{template['id']}/file", headers=admin)
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")

    assert client.delete(f"/api/v1/documents/templates/{template['id']}", headers=admin).status_code == 204
    assert client.get("/api/v1/documents/templates", headers=admin).json() == []


def test_create_document_from_template_seeds_the_file(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    template = _upload_template(client, admin).json()

    # Crear documento SIN adjuntar archivo, sembrando desde la plantilla.
    resp = client.post(
        "/api/v1/documents",
        data={"code": "POL-700", "title": "Nueva política", "document_type": "policy", "template_id": template["id"]},
        headers=admin,
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    # La versión 1 tomó el binario de la plantilla → se puede descargar.
    dl = client.get(f"/api/v1/documents/{doc['id']}/versions/1/file", headers=admin)
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")

    # Ni archivo ni plantilla → 422.
    resp = client.post(
        "/api/v1/documents",
        data={"code": "POL-701", "title": "Sin base", "document_type": "policy"},
        headers=admin,
    )
    assert resp.status_code == 422


def test_templates_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    template = _upload_template(client, auth_headers(tenant_a["id"])).json()

    # El tenant B no la ve ni puede usarla para crear.
    assert client.get("/api/v1/documents/templates", headers=auth_headers(tenant_b["id"])).json() == []
    resp = client.post(
        "/api/v1/documents",
        data={"code": "POL-800", "title": "Ajeno", "document_type": "policy", "template_id": template["id"]},
        headers=auth_headers(tenant_b["id"]),
    )
    assert resp.status_code == 404
