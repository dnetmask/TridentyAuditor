"""Tanda COMP — respuesta al análisis de competencia (Kawak).

Cubre: evaluación del auditor (COMP-A), % avance + costo en CAPA (COMP-B),
dashboard de higiene documental (COMP-C) y verificación de integridad visible
(COMP-D).
"""

from datetime import date, timedelta

from app.documents import storage


def _approve_document(client, headers, code="EVID-COMP"):
    resp = client.post(
        "/api/v1/documents",
        data={"code": code, "title": "Evidencia CAPA", "document_type": "record"},
        files={"file": ("evidencia.pdf", b"%PDF-1.4 evidencia comp", "application/pdf")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/versions/1/submit", headers=headers)
    resp = client.post(f"/api/v1/documents/{doc_id}/versions/1/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    return doc_id


def _new_program(client, headers, title="Auditoría COMP"):
    return client.post("/api/v1/audit/programs", json={"title": title}, headers=headers).json()["id"]


# ---------------------------------------------------------------------------
# COMP-A — evaluación del auditor líder al cerrar la auditoría
# ---------------------------------------------------------------------------


def test_auditor_evaluation_only_when_completed(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = _new_program(client, headers)

    # En estado planned no se puede evaluar al auditor.
    resp = client.patch(
        f"/api/v1/audit/programs/{program_id}",
        json={"auditor_score": 5, "auditor_evaluation": "Excelente"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text

    # Al cerrar la auditoría sí, y los valores persisten.
    resp = client.patch(
        f"/api/v1/audit/programs/{program_id}",
        json={"status": "completed", "auditor_score": 4, "auditor_evaluation": "Buen desempeño"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["auditor_score"] == 4
    assert body["auditor_evaluation"] == "Buen desempeño"


def test_auditor_score_out_of_range_rejected(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = _new_program(client, headers)
    client.patch(f"/api/v1/audit/programs/{program_id}", json={"status": "completed"}, headers=headers)

    resp = client.patch(
        f"/api/v1/audit/programs/{program_id}",
        json={"auditor_score": 6},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# COMP-B — % de avance y costo estimado en la acción CAPA
# ---------------------------------------------------------------------------


def test_finding_progress_and_cost_persist(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = _new_program(client, headers)

    resp = client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": program_id,
            "classification": "minor_nc",
            "description": "Falta control de accesos",
            "progress_pct": 40,
            "estimated_cost": 1500000,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    finding = resp.json()
    assert finding["progress_pct"] == 40
    assert finding["estimated_cost"] == 1500000.0

    resp = client.patch(
        f"/api/v1/audit/findings/{finding['id']}",
        json={"progress_pct": 80},
        headers=headers,
    )
    assert resp.json()["progress_pct"] == 80


def test_closing_finding_forces_progress_100(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = _new_program(client, headers)
    finding_id = client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": program_id,
            "classification": "major_nc",
            "description": "Hallazgo grave",
            "progress_pct": 30,
        },
        headers=headers,
    ).json()["id"]

    approved_doc = _approve_document(client, headers, code="CAPA-CLOSE-100")
    resp = client.patch(
        f"/api/v1/audit/findings/{finding_id}",
        json={"status": "closed", "evidence_document_id": approved_doc},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "closed"
    assert body["progress_pct"] == 100


def test_summary_capa_aggregates(client, make_tenant, auth_headers):
    tenant = make_tenant()
    headers = auth_headers(tenant["id"])
    program_id = _new_program(client, headers)
    client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": program_id,
            "classification": "minor_nc",
            "description": "a",
            "progress_pct": 40,
            "estimated_cost": 1000,
        },
        headers=headers,
    )
    client.post(
        "/api/v1/audit/findings",
        json={
            "audit_id": program_id,
            "classification": "observation",
            "description": "b",
            "progress_pct": 60,
            "estimated_cost": 3000,
        },
        headers=headers,
    )

    body = client.get("/api/v1/audit/summary", headers=headers).json()
    assert body["capa_open_avg_progress"] == 50
    assert body["capa_open_estimated_cost"] == 4000.0


# ---------------------------------------------------------------------------
# COMP-C — dashboard de higiene documental
# ---------------------------------------------------------------------------


def test_hygiene_shape_empty_tenant(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    data = client.get("/api/v1/dashboard/overview", headers=admin).json()
    assert "documental_hygiene" in data
    hyg = data["documental_hygiene"]
    assert hyg["total"] == 0
    assert hyg["pct_current"] == 100
    assert hyg["avg_implementation_days"] == 0


def test_hygiene_counts_overdue_upcoming_unscheduled(
    client, make_tenant, auth_headers, upload_document
):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    today = date.today()

    # Vencido (fecha de revisión en el pasado).
    upload_document(
        admin, code="POL-HYG-OVERDUE",
        extra_fields={"next_review_date": (today - timedelta(days=10)).isoformat()},
    )
    # Al día (fecha de revisión lejana).
    upload_document(
        admin, code="POL-HYG-CURRENT",
        extra_fields={"next_review_date": (today + timedelta(days=200)).isoformat()},
    )
    # Sin programar (sin fecha de revisión).
    upload_document(admin, code="POL-HYG-NONE")

    hyg = client.get("/api/v1/dashboard/overview", headers=admin).json()["documental_hygiene"]
    assert hyg["total"] == 3
    assert hyg["overdue"] == 1
    assert hyg["current"] == 1
    assert hyg["unscheduled"] == 1
    assert hyg["scheduled"] == 2
    # 2 programados, 1 vencido → 50% al día.
    assert hyg["pct_current"] == 50


def test_hygiene_avg_implementation_days(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-HYG-IMPL").json()
    client.post(f"/api/v1/documents/{doc['id']}/versions/1/submit", headers=admin)
    client.post(f"/api/v1/documents/{doc['id']}/versions/1/approve", headers=admin)

    hyg = client.get("/api/v1/dashboard/overview", headers=admin).json()["documental_hygiene"]
    assert hyg["implemented_docs"] == 1
    assert hyg["avg_implementation_days"] >= 0


# ---------------------------------------------------------------------------
# COMP-D — verificación de integridad visible
# ---------------------------------------------------------------------------


def test_verify_reports_verified_and_hash(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-VER-1").json()

    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/1/verify", headers=admin)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verified"] is True
    assert body["has_hash"] is True
    assert body["file_present"] is True
    assert body["algorithm"] == "SHA-256"
    assert body["expected_sha256"] == body["actual_sha256"]
    assert len(body["expected_sha256"]) == 64
    assert body["approvals"] == []


def test_verify_includes_approval_seals(client, make_tenant, auth_headers):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc_id = _approve_document(client, admin, code="POL-VER-SEALS")

    body = client.get(f"/api/v1/documents/{doc_id}/versions/1/verify", headers=admin).json()
    assert body["verified"] is True
    assert len(body["approvals"]) >= 1
    seal = body["approvals"][0]
    assert seal["step"]
    assert seal["signed_by"]
    assert seal["matches_current"] is True


def test_verify_detects_tampering(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-VER-TAMPER").json()

    # Adulterar el binario en el almacenamiento por detrás de la app.
    doc_dir = storage._root() / tenant["id"] / doc["id"]
    for path in doc_dir.glob("*"):
        path.write_bytes(b"contenido adulterado")

    body = client.get(f"/api/v1/documents/{doc['id']}/versions/1/verify", headers=admin).json()
    assert body["verified"] is False
    assert body["expected_sha256"] != body["actual_sha256"]


def test_verify_unknown_version_404(client, make_tenant, auth_headers, upload_document):
    tenant = make_tenant()
    admin = auth_headers(tenant["id"])
    doc = upload_document(admin, code="POL-VER-404").json()
    resp = client.get(f"/api/v1/documents/{doc['id']}/versions/99/verify", headers=admin)
    assert resp.status_code == 404
