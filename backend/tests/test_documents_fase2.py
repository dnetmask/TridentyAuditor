"""Fase 2: aprobación multinivel — firma del gerente de área + firma de
seguridad de la información, con sello SHA-256 por firma."""


def _create_area(client, headers, name="Tecnología", manager_user_id=None):
    payload = {"name": name}
    if manager_user_id is not None:
        payload["manager_user_id"] = manager_user_id
    resp = client.post("/api/v1/areas", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _directory_id(client, headers, full_name):
    directory = client.get("/api/v1/auth/directory", headers=headers).json()
    return next(u["id"] for u in directory if u["full_name"] == full_name)


def _submit(client, headers, doc_id, version=1):
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/{version}/submit", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _approve(client, headers, doc_id, version=1):
    return client.post(f"/api/v1/documents/{doc_id}/versions/{version}/approve", headers=headers)


# ------------------------------------------------ sin área: una sola firma

def test_document_without_area_needs_single_security_signature(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-201").json()
    _submit(client, admin, doc["id"])

    resp = _approve(client, admin, doc["id"])
    assert resp.status_code == 200, resp.text
    version = resp.json()
    assert version["status"] == "approved"
    assert [a["step"] for a in version["approvals"]] == ["security"]
    # El sello queda amarrado al binario exacto que se aprobó.
    assert version["approvals"][0]["file_sha256"] == version["file_sha256"]
    assert version["approvals"][0]["file_sha256"] is not None


def test_non_admin_cannot_sign_security_step(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    auditor = auth_headers(tenant["id"], role="internal_auditor")
    doc = upload_document(admin, code="POL-202").json()
    _submit(client, admin, doc["id"])

    assert _approve(client, auditor, doc["id"]).status_code == 403


# ------------------------------------------------ con área: dos firmas

def test_document_with_area_requires_two_signatures_in_order(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    # El gerente del área es un auditor interno — NO admin.
    auth_headers(tenant["id"], role="internal_auditor", email="gerente@example.com", full_name="Gerente Área")
    manager_id = _directory_id(client, admin, "Gerente Área")
    area = _create_area(client, admin, name="Gestión Humana", manager_user_id=manager_id)

    doc = upload_document(admin, code="PRC-201", extra_fields={"area_id": area["id"]}).json()
    _submit(client, admin, doc["id"])

    manager = auth_headers(tenant["id"], role="internal_auditor", email="gerente@example.com", full_name="Gerente Área")

    # Un visualizador cualquiera no puede firmar el paso del gerente.
    viewer = auth_headers(tenant["id"], role="viewer")
    assert _approve(client, viewer, doc["id"]).status_code == 403

    # Firma 1: el gerente del área. La versión NO queda aprobada todavía.
    resp = _approve(client, manager, doc["id"])
    assert resp.status_code == 200, resp.text
    version = resp.json()
    assert version["status"] == "in_review"
    assert [a["step"] for a in version["approvals"]] == ["area_manager"]
    assert version["approvals"][0]["signed_by"] == "gerente@example.com"

    # El gerente no puede firmar también el paso de seguridad.
    assert _approve(client, manager, doc["id"]).status_code == 403

    # Firma 2: seguridad de la información (Admin) → publica.
    resp = _approve(client, admin, doc["id"])
    assert resp.status_code == 200, resp.text
    version = resp.json()
    assert version["status"] == "approved"
    assert [a["step"] for a in version["approvals"]] == ["area_manager", "security"]
    assert version["approved_by"] is not None


def test_admin_can_sign_in_place_of_area_manager(
    client, make_tenant, auth_headers, upload_document
):
    """Área sin gerente asignado (o gerente ausente): un Admin firma en su lugar."""
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    area = _create_area(client, admin, name="Proyectos")

    doc = upload_document(admin, code="REG-201", extra_fields={"area_id": area["id"]}).json()
    _submit(client, admin, doc["id"])

    first = _approve(client, admin, doc["id"]).json()
    assert first["status"] == "in_review"
    assert [a["step"] for a in first["approvals"]] == ["area_manager"]

    second = _approve(client, admin, doc["id"]).json()
    assert second["status"] == "approved"
    assert len(second["approvals"]) == 2


def test_reject_clears_partial_signatures(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    area = _create_area(client, admin, name="Comercial")
    doc = upload_document(admin, code="POL-203", extra_fields={"area_id": area["id"]}).json()
    _submit(client, admin, doc["id"])

    assert _approve(client, admin, doc["id"]).json()["approvals"] != []

    resp = client.post(
        f"/api/v1/documents/{doc['id']}/versions/1/reject",
        json={"reason": "Falta la sección de alcance"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["approvals"] == []

    # Reenvío: la aprobación arranca desde cero (vuelve a pedir ambas firmas).
    _submit(client, admin, doc["id"])
    version = _approve(client, admin, doc["id"]).json()
    assert version["status"] == "in_review"
    assert [a["step"] for a in version["approvals"]] == ["area_manager"]


def test_two_signature_approval_rolls_review_date_and_obsoletes_previous(
    client, make_tenant, auth_headers, upload_document, upload_version
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    area = _create_area(client, admin, name="Dirección")
    doc = upload_document(
        admin,
        code="POL-204",
        extra_fields={"area_id": area["id"], "review_frequency_months": "6"},
    ).json()
    _submit(client, admin, doc["id"])
    _approve(client, admin, doc["id"])
    _approve(client, admin, doc["id"])

    upload_version(admin, doc["id"], change_summary="Segunda versión")
    _submit(client, admin, doc["id"], version=2)
    _approve(client, admin, doc["id"], version=2)
    resp = _approve(client, admin, doc["id"], version=2)
    assert resp.json()["status"] == "approved"

    detail = client.get(f"/api/v1/documents/{doc['id']}", headers=admin).json()
    statuses = {v["version_number"]: v["status"] for v in detail["versions"]}
    assert statuses == {1: "obsolete", 2: "approved"}
    assert detail["next_review_date"] is not None
