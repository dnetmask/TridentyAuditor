"""MOD·PRC (Fase 4): mapa de procesos — CRUD, jerarquía, enlaces a
documentos, árbol con conteo acumulado y aislamiento por tenant."""


def _create(client, headers, name, **overrides):
    payload = {"name": name}
    payload.update(overrides)
    resp = client.post("/api/v1/processes", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_process_crud_and_role_guard(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    viewer = auth_headers(tenant["id"], role="viewer")

    proc = _create(client, admin, "Gestión Humana", description="Procesos de personas")
    assert proc["name"] == "Gestión Humana"

    # Duplicado por nombre → 409.
    assert client.post("/api/v1/processes", json={"name": "Gestión Humana"}, headers=admin).status_code == 409

    # Lee cualquiera; escribe solo el admin.
    assert client.get("/api/v1/processes", headers=viewer).status_code == 200
    assert client.post("/api/v1/processes", json={"name": "Otro"}, headers=viewer).status_code == 403

    # Editar y borrar.
    resp = client.patch(f"/api/v1/processes/{proc['id']}", json={"description": "Actualizado"}, headers=admin)
    assert resp.status_code == 200
    assert resp.json()["description"] == "Actualizado"
    assert client.delete(f"/api/v1/processes/{proc['id']}", headers=admin).status_code == 204


def test_hierarchy_and_cycle_guard(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    parent = _create(client, admin, "Dirección")
    child = _create(client, admin, "Planeación", parent_id=parent["id"])
    assert child["parent_id"] == parent["id"]

    # Un proceso no puede ser su propio padre.
    assert client.patch(
        f"/api/v1/processes/{parent['id']}", json={"parent_id": parent["id"]}, headers=admin
    ).status_code == 422
    # Ni formar un ciclo (el padre no puede colgar de su hijo).
    assert client.patch(
        f"/api/v1/processes/{parent['id']}", json={"parent_id": child["id"]}, headers=admin
    ).status_code == 422


def test_tree_with_documents_and_accumulated_count(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc1 = upload_document(admin, code="POL-PRC-1").json()
    doc2 = upload_document(admin, code="POL-PRC-2").json()

    parent = _create(client, admin, "Operación", document_ids=[doc1["id"]])
    _create(client, admin, "Soporte", parent_id=parent["id"], document_ids=[doc2["id"]])

    tree = client.get("/api/v1/processes/tree", headers=admin).json()
    assert len(tree) == 1  # una raíz
    root = tree[0]
    assert root["name"] == "Operación"
    assert [d["code"] for d in root["documents"]] == ["POL-PRC-1"]
    assert len(root["children"]) == 1
    assert root["children"][0]["documents"][0]["code"] == "POL-PRC-2"
    # El conteo de la raíz acumula el documento del subproceso.
    assert root["document_count"] == 2
    assert root["children"][0]["document_count"] == 1


def test_document_links_replace_set_and_validation(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-PRC-3").json()
    proc = _create(client, admin, "Comercial", document_ids=[doc["id"]])

    # Reemplazar por conjunto vacío quita el enlace.
    client.patch(f"/api/v1/processes/{proc['id']}", json={"document_ids": []}, headers=admin)
    tree = client.get("/api/v1/processes/tree", headers=admin).json()
    node = next(p for p in tree if p["id"] == proc["id"])
    assert node["documents"] == []

    # Un documento inexistente → 422.
    assert client.post(
        "/api/v1/processes",
        json={"name": "X", "document_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=admin,
    ).status_code == 422


def test_processes_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    _create(client, auth_headers(tenant_a["id"]), "Proceso privado de A")

    listing_b = client.get("/api/v1/processes", headers=auth_headers(tenant_b["id"])).json()
    assert all(p["name"] != "Proceso privado de A" for p in listing_b)


def test_owner_must_belong_to_tenant(client, make_tenant, auth_headers):
    tenant = make_tenant()
    other = make_tenant()
    admin = auth_headers(tenant["id"])
    auth_headers(other["id"], email="ajeno-prc@example.com")
    foreign_id = client.get("/api/v1/auth/directory", headers=auth_headers(other["id"])).json()[0]["id"]
    assert client.post(
        "/api/v1/processes", json={"name": "Con dueño ajeno", "owner_user_id": foreign_id}, headers=admin
    ).status_code == 422
