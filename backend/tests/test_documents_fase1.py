"""Fase 1: clasificación (áreas, controles, origen), fechas de revisión,
numeración sugerida, edición de metadatos, derogación e integridad."""

from datetime import date


def _control_ids(client, count=2):
    domains = client.get("/api/v1/frameworks/ISO27001:2022/domains").json()
    return [c["id"] for c in domains[0]["controls"][:count]]


def _create_area(client, headers, name="Tecnología"):
    resp = client.post("/api/v1/areas", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------------------ áreas

def test_area_crud_and_manager_validation(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    viewer = auth_headers(tenant["id"], role="viewer")

    area = _create_area(client, admin, name="Seguridad de la Información")

    # Nombre duplicado en el mismo tenant → 409.
    resp = client.post("/api/v1/areas", json={"name": "Seguridad de la Información"}, headers=admin)
    assert resp.status_code == 409

    # Cualquier rol del tenant puede listarlas; solo el admin las gestiona.
    resp = client.get("/api/v1/areas", headers=viewer)
    assert resp.status_code == 200
    assert any(a["id"] == area["id"] for a in resp.json())
    assert client.post("/api/v1/areas", json={"name": "Otra"}, headers=viewer).status_code == 403

    # El gerente debe ser un usuario activo DEL MISMO tenant.
    other_tenant = make_tenant()
    other_admin_token_headers = auth_headers(other_tenant["id"], email="gerente-ajeno@example.com")
    del other_admin_token_headers  # el usuario quedó creado en el otro tenant
    directory = client.get("/api/v1/auth/directory", headers=auth_headers(other_tenant["id"]))
    foreign_user_id = directory.json()[0]["id"]
    resp = client.patch(
        f"/api/v1/areas/{area['id']}", json={"manager_user_id": foreign_user_id}, headers=admin
    )
    assert resp.status_code == 422


def test_areas_are_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    _create_area(client, auth_headers(tenant_a["id"]), name="Área privada de A")

    listing_b = client.get("/api/v1/areas", headers=auth_headers(tenant_b["id"])).json()
    assert all(a["name"] != "Área privada de A" for a in listing_b)


# ------------------------------------------------- clasificación al crear

def test_create_document_with_area_controls_and_dates(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    area = _create_area(client, headers)
    control_ids = _control_ids(client)

    resp = upload_document(
        headers,
        code="POL-100",
        control_ids=control_ids,
        extra_fields={
            "area_id": area["id"],
            "implementation_date": "2026-01-15",
            "review_frequency_months": "12",
            "next_review_date": "2027-01-15",
        },
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    assert doc["area"]["name"] == "Tecnología"
    assert doc["implementation_date"] == "2026-01-15"
    assert doc["review_frequency_months"] == 12
    assert sorted(c["id"] for c in doc["controls"]) == sorted(control_ids)
    assert doc["origin"] == "internal"
    assert doc["versions"][0]["file_sha256"] is not None


def test_create_document_with_unknown_control_is_422(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(
        headers, code="POL-101", control_ids=["00000000-0000-0000-0000-000000000000"]
    )
    assert resp.status_code == 422


def test_external_origin_keeps_source(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    resp = upload_document(
        headers,
        code="EXT-001",
        extra_fields={"origin": "external", "external_source": "Consejo Nacional de Operación"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["origin"] == "external"
    assert resp.json()["external_source"] == "Consejo Nacional de Operación"


# ------------------------------------------------------ numeración sugerida

def test_next_code_suggests_consecutive_per_type(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    resp = client.get("/api/v1/documents/next-code", params={"document_type": "policy"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == "POL-001"

    upload_document(headers, code="POL-001")
    upload_document(headers, code="POL-007")
    upload_document(headers, code="CODIGO-LIBRE")  # fuera del patrón: no estorba

    resp = client.get("/api/v1/documents/next-code", params={"document_type": "policy"}, headers=headers)
    assert resp.json()["code"] == "POL-008"

    # Otro tipo lleva su propio consecutivo.
    resp = client.get("/api/v1/documents/next-code", params={"document_type": "procedure"}, headers=headers)
    assert resp.json()["code"] == "PRC-001"


# ------------------------------------------------------- edición y derogación

def test_patch_document_updates_metadata_and_replaces_controls(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    control_ids = _control_ids(client, count=3)
    doc_id = upload_document(headers, code="PRC-050", control_ids=control_ids[:2]).json()["id"]

    resp = client.patch(
        f"/api/v1/documents/{doc_id}",
        json={
            "title": "Procedimiento corregido",
            "review_frequency_months": 6,
            "control_ids": [control_ids[2]],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Procedimiento corregido"
    assert body["review_frequency_months"] == 6
    assert [c["id"] for c in body["controls"]] == [control_ids[2]]  # reemplazo total

    # Viewer no puede editar.
    viewer = auth_headers(tenant["id"], role="viewer")
    resp = client.patch(f"/api/v1/documents/{doc_id}", json={"title": "x"}, headers=viewer)
    assert resp.status_code == 403


def test_retire_document_requires_reason_and_blocks_changes(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc_id = upload_document(headers, code="POL-090").json()["id"]

    resp = client.post(f"/api/v1/documents/{doc_id}/retire", json={"reason": ""}, headers=headers)
    assert resp.status_code == 422  # motivo obligatorio

    resp = client.post(
        f"/api/v1/documents/{doc_id}/retire",
        json={"reason": "Reemplazada por la política corporativa v2"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["retired_at"] is not None
    assert body["retirement_reason"] == "Reemplazada por la política corporativa v2"

    # Derogado: sin ediciones, sin versiones nuevas, sin re-derogar.
    assert client.patch(f"/api/v1/documents/{doc_id}", json={"title": "x"}, headers=headers).status_code == 409
    resp = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        data={"change_summary": "intento"},
        files={"file": ("v2.pdf", b"%PDF-1.4 v2", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 409
    assert (
        client.post(f"/api/v1/documents/{doc_id}/retire", json={"reason": "otra vez"}, headers=headers).status_code
        == 409
    )

    # El auditor interno no puede derogar (acto de autoridad).
    auditor = auth_headers(tenant["id"], role="internal_auditor")
    other_id = upload_document(headers, code="POL-091").json()["id"]
    resp = client.post(f"/api/v1/documents/{other_id}/retire", json={"reason": "x"}, headers=auditor)
    assert resp.status_code == 403


def test_retired_document_stops_counting_as_approved_evidence(
    client, make_tenant, auth_headers, upload_document
):
    """Derogar saca al documento de la evidencia válida: una tarea del wizard
    que exige evidencia ya no se puede cerrar apuntando a él."""
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    doc_id = upload_document(headers, code="EVID-RET-001").json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)

    client.post("/api/v1/wizard/instantiate", headers=headers)
    progress = client.get("/api/v1/wizard/progress", headers=headers).json()
    task = next(t for t in progress[0]["tasks"] if t["requires_evidence"])
    client.patch(
        f"/api/v1/wizard/tasks/{task['id']}", json={"evidence_document_id": doc_id}, headers=headers
    )

    # Con el documento vigente, la tarea cierra.
    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 200
    client.post(f"/api/v1/wizard/tasks/{task['id']}/reopen", headers=headers)

    # Derogado, la misma evidencia deja de valer.
    client.post(f"/api/v1/documents/{doc_id}/retire", json={"reason": "obsoleta"}, headers=headers)
    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 409


# --------------------------------------------- versiones: cambios e integridad

def test_new_version_requires_change_summary(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc_id = upload_document(headers, code="PRC-070").json()["id"]

    resp = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        files={"file": ("v2.pdf", b"%PDF-1.4 v2", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 422  # sin resumen de cambios no hay versión nueva


def test_approving_rolls_next_review_date_from_frequency(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc_id = upload_document(
        headers, code="POL-080", extra_fields={"review_frequency_months": "12"}
    ).json()["id"]

    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)

    doc = client.get(f"/api/v1/documents/{doc_id}", headers=headers).json()
    next_review = date.fromisoformat(doc["next_review_date"])
    today = date.today()
    assert (next_review.year - today.year) * 12 + (next_review.month - today.month) == 12


def test_tampered_file_is_not_served(client, make_tenant, auth_headers, upload_document):
    from sqlalchemy import select, text

    from app.core.database import SessionLocal
    from app.documents import storage
    from app.documents.models import DocumentVersion

    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    doc_id = upload_document(headers, code="INT-001", content=b"%PDF-1.4 original").json()["id"]

    # Adulterar el binario por fuera de la plataforma. La sesión cruda debe
    # fijar app.tenant_id para pasar la política RLS de document_versions.
    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant["id"]})
        version = db.scalars(
            select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        ).first()
        storage.path_for(version.storage_ref).write_bytes(b"%PDF-1.4 ADULTERADO")

    resp = client.get(f"/api/v1/documents/{doc_id}/versions/1/file", headers=headers)
    assert resp.status_code == 500
    assert "integridad" in resp.json()["detail"].lower()
