"""MOD·LEG: matriz de requisitos legales — CRUD, aislamiento, calificación
de cumplimiento y su componente en el indicador global."""


def _create_requirement(client, headers, name="Ley 1581 de 2012", **overrides):
    payload = {
        "requirement_type": "law",
        "name": name,
        "issuer": "Congreso de Colombia",
        "publication_year": 2012,
        "articles": "Toda la ley",
        "description": "Regula el tratamiento de datos personales.",
        "topic": "Protección de datos personales",
        "review_frequency_months": 12,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/legal-requirements", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_list_requirements(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    viewer = auth_headers(tenant["id"], role="viewer")

    requirement = _create_requirement(client, admin)
    assert requirement["status"] == "in_force"
    assert requirement["compliance_rating"] == "not_evaluated"

    # Nombre duplicado en el mismo tenant → 409.
    resp = client.post(
        "/api/v1/legal-requirements",
        json={"requirement_type": "law", "name": "Ley 1581 de 2012"},
        headers=admin,
    )
    assert resp.status_code == 409

    # El visualizador lee pero no escribe.
    listing = client.get("/api/v1/legal-requirements", headers=viewer)
    assert listing.status_code == 200
    assert any(r["id"] == requirement["id"] for r in listing.json())
    resp = client.post(
        "/api/v1/legal-requirements",
        json={"requirement_type": "decree", "name": "Decreto 1377 de 2013"},
        headers=viewer,
    )
    assert resp.status_code == 403


def test_requirements_are_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    requirement = _create_requirement(client, auth_headers(tenant_a["id"]), name="Ley privada de A")

    listing_b = client.get(
        "/api/v1/legal-requirements", headers=auth_headers(tenant_b["id"])
    ).json()
    assert all(r["name"] != "Ley privada de A" for r in listing_b)
    # Ni siquiera por id directo (RLS).
    resp = client.patch(
        f"/api/v1/legal-requirements/{requirement['id']}",
        json={"topic": "intento ajeno"},
        headers=auth_headers(tenant_b["id"]),
    )
    assert resp.status_code == 404


def test_responsible_must_be_active_user_of_tenant(client, make_tenant, auth_headers):
    tenant = make_tenant()
    other = make_tenant()
    admin = auth_headers(tenant["id"])
    auth_headers(other["id"], email="ajeno@example.com")  # usuario del OTRO tenant
    directory_other = client.get(
        "/api/v1/auth/directory", headers=auth_headers(other["id"])
    ).json()
    foreign_id = directory_other[0]["id"]

    resp = client.post(
        "/api/v1/legal-requirements",
        json={"requirement_type": "law", "name": "Ley 1266 de 2008", "responsible_user_id": foreign_id},
        headers=admin,
    )
    assert resp.status_code == 422


def test_evidence_document_must_belong_to_tenant(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    other = make_tenant()
    admin = auth_headers(tenant["id"])
    foreign_doc = upload_document(auth_headers(other["id"]), code="POL-LEG-AJENA").json()

    resp = client.post(
        "/api/v1/legal-requirements",
        json={
            "requirement_type": "law",
            "name": "Ley 1273 de 2009",
            "evidence_document_id": foreign_doc["id"],
        },
        headers=admin,
    )
    assert resp.status_code == 422

    # Con un documento propio sí.
    own_doc = upload_document(admin, code="POL-LEG-01").json()
    requirement = _create_requirement(
        client, admin, name="Ley 1273 de 2009", evidence_document_id=own_doc["id"]
    )
    assert requirement["evidence_document_id"] == own_doc["id"]


def test_rating_status_and_summary(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])

    compliant = _create_requirement(client, admin, name="Ley 1581 de 2012")
    partial = _create_requirement(client, admin, name="Decreto 1377 de 2013", requirement_type="decree")
    repealed = _create_requirement(client, admin, name="Norma vieja", requirement_type="standard")

    for req, rating in ((compliant, "compliant"), (partial, "partial")):
        resp = client.patch(
            f"/api/v1/legal-requirements/{req['id']}",
            json={"compliance_rating": rating},
            headers=admin,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["compliance_rating"] == rating

    resp = client.patch(
        f"/api/v1/legal-requirements/{repealed['id']}",
        json={"status": "repealed"},
        headers=admin,
    )
    assert resp.json()["status"] == "repealed"

    # Vigentes: 1 cumple + 1 parcial (0.5) sobre 2 → 75%. La derogada no cuenta.
    summary = client.get("/api/v1/legal-requirements/summary", headers=admin).json()
    assert summary["total"] == 2
    assert summary["compliant"] == 1
    assert summary["partial"] == 1
    assert summary["percentage"] == 75.0


def test_compliance_overview_gains_legal_component_only_when_matrix_exists(
    client, make_tenant, auth_headers
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])

    # Sin requisitos: la fórmula original (SoA + wizard), sin componente legal.
    overview = client.get("/api/v1/compliance/overview", headers=admin).json()
    assert [c["key"] for c in overview["components"]] == ["soa", "wizard"]

    requirement = _create_requirement(client, admin)
    client.patch(
        f"/api/v1/legal-requirements/{requirement['id']}",
        json={"compliance_rating": "compliant"},
        headers=admin,
    )

    overview = client.get("/api/v1/compliance/overview", headers=admin).json()
    keys = [c["key"] for c in overview["components"]]
    assert keys == ["soa", "wizard", "legal"]
    legal = overview["components"][2]
    assert legal["total"] == 1
    assert legal["evidenced"] == 1
    assert legal["percentage"] == 100.0
    # SoA y wizard en 0 → el global es exactamente el peso del componente legal.
    assert overview["percentage"] == 20.0
