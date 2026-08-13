def _approve_document(client, headers, code="EVID-001"):
    resp = client.post(
        "/api/v1/documents",
        data={"code": code, "title": "Evidencia de prueba", "document_type": "record"},
        files={"file": ("evidencia.pdf", b"%PDF-1.4 evidencia", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    return doc_id


def _instantiate(client, headers):
    resp = client.post("/api/v1/wizard/instantiate", headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _progress(client, headers):
    resp = client.get("/api/v1/wizard/progress", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_instantiate_is_idempotent_and_seeds_all_eight_phases(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])

    first = _instantiate(client, headers)
    assert first["created"] > 0

    second = _instantiate(client, headers)
    assert second["created"] == 0

    progress = _progress(client, headers)
    assert len(progress) == 8
    assert [p["phase"]["number"] for p in progress] == list(range(1, 9))
    assert progress[0]["status"] == "current"
    assert all(p["status"] == "locked" for p in progress[1:])
    assert all(p["total_count"] > 0 for p in progress)


def test_task_requiring_evidence_blocks_completion_until_approved(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    _instantiate(client, headers)

    progress = _progress(client, headers)
    task = next(t for t in progress[0]["tasks"] if t["requires_evidence"])

    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 409

    resp = client.post(
        "/api/v1/documents",
        data={"code": "DRAFT-001", "title": "Aún sin aprobar", "document_type": "record"},
        files={"file": ("draft.pdf", b"%PDF-1.4 draft", "application/pdf")},
        headers=headers,
    )
    draft_doc_id = resp.json()["id"]
    resp = client.patch(
        f"/api/v1/wizard/tasks/{task['id']}", json={"evidence_document_id": draft_doc_id}, headers=headers
    )
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 409

    approved_doc_id = _approve_document(client, headers, code="EVID-APPROVED-001")
    client.patch(
        f"/api/v1/wizard/tasks/{task['id']}", json={"evidence_document_id": approved_doc_id}, headers=headers
    )
    resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_phase_locked_until_previous_phase_fully_done(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    _instantiate(client, headers)

    progress = _progress(client, headers)
    phase3_task = progress[2]["tasks"][0]

    # Fulfilling evidence alone isn't enough — phase 1 and 2 aren't done yet.
    if phase3_task["requires_evidence"]:
        doc_id = _approve_document(client, headers, code="PHASE3-EVID")
        client.patch(
            f"/api/v1/wizard/tasks/{phase3_task['id']}",
            json={"evidence_document_id": doc_id},
            headers=headers,
        )
    resp = client.post(f"/api/v1/wizard/tasks/{phase3_task['id']}/complete", headers=headers)
    assert resp.status_code == 409

    # Complete every phase-1 task.
    for task in progress[0]["tasks"]:
        if task["requires_evidence"]:
            doc_id = _approve_document(client, headers, code=f"P1-{task['id'][:8]}")
            client.patch(
                f"/api/v1/wizard/tasks/{task['id']}", json={"evidence_document_id": doc_id}, headers=headers
            )
        resp = client.post(f"/api/v1/wizard/tasks/{task['id']}/complete", headers=headers)
        assert resp.status_code == 200, resp.text

    progress = _progress(client, headers)
    assert progress[0]["status"] == "complete"
    assert progress[1]["status"] == "current"
    assert progress[2]["status"] == "locked"


def test_reopen_task_reverts_phase_status(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    _instantiate(client, headers)

    progress = _progress(client, headers)
    no_evidence_task = next(t for t in progress[0]["tasks"] if not t["requires_evidence"])

    resp = client.post(f"/api/v1/wizard/tasks/{no_evidence_task['id']}/reopen", headers=headers)
    assert resp.status_code == 409  # not done yet

    resp = client.post(f"/api/v1/wizard/tasks/{no_evidence_task['id']}/complete", headers=headers)
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/wizard/tasks/{no_evidence_task['id']}/reopen", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["completed_at"] is None


def test_wizard_progress_is_isolated_per_tenant(client, make_tenant, auth_headers):
    tenant_a = make_tenant()
    tenant_b = make_tenant()
    headers_a = auth_headers(tenant_a["id"])
    headers_b = auth_headers(tenant_b["id"])

    _instantiate(client, headers_a)

    progress_a = _progress(client, headers_a)
    progress_b = _progress(client, headers_b)

    assert progress_a[0]["total_count"] > 0
    assert progress_b[0]["total_count"] == 0  # tenant B never instantiated its own checklist


def test_custom_task_can_be_added_to_a_phase(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    _instantiate(client, headers)

    progress = _progress(client, headers)
    phase_id = progress[0]["phase"]["id"]

    resp = client.post(
        "/api/v1/wizard/tasks",
        json={
            "phase_id": phase_id,
            "title": "Tarea adicional definida por el tenant",
            "requires_evidence": False,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["template_id"] is None

    progress = _progress(client, headers)
    assert progress[0]["total_count"] == 4  # 3 del checklist + 1 custom
