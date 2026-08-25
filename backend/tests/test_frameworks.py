def test_iso27001_seed_loaded(client):
    resp = client.get("/api/v1/frameworks/ISO27001:2022")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "ISO27001:2022"
    assert len(data["domains"]) == 4
    total_controls = sum(len(d["controls"]) for d in data["domains"])
    assert total_controls == 93


def test_domain_control_counts_match_annex_a(client):
    resp = client.get("/api/v1/frameworks/ISO27001:2022/domains")
    assert resp.status_code == 200
    counts = {d["code"]: len(d["controls"]) for d in resp.json()}
    assert counts == {"A.5": 37, "A.6": 8, "A.7": 14, "A.8": 34}


def test_control_detail_includes_empty_requirements(client):
    resp = client.get("/api/v1/frameworks/ISO27001:2022/domains")
    first_domain = resp.json()[0]
    control_id = first_domain["controls"][0]["id"]

    resp = client.get(f"/api/v1/controls/{control_id}")
    assert resp.status_code == 200
    assert resp.json()["requirements"] == []


def test_controls_carry_evidence_guidance(client):
    resp = client.get("/api/v1/frameworks/ISO27001:2022/domains")
    for domain in resp.json():
        for control in domain["controls"]:
            assert control["evidence_guidance"], f"{control['code']} sin guía de evidencia"


def test_unknown_framework_returns_404(client):
    resp = client.get("/api/v1/frameworks/NOPE")
    assert resp.status_code == 404


def test_list_frameworks_includes_both_normas(client):
    resp = client.get("/api/v1/frameworks")
    assert resp.status_code == 200
    codes = {f["code"] for f in resp.json()}
    assert {"ISO27001:2022", "CNO-1960"} <= codes


def test_cno1960_seed_loaded_with_10_domains_and_41_controls(client):
    resp = client.get("/api/v1/frameworks/CNO-1960")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "CNO-1960"
    assert len(data["domains"]) == 10
    total_controls = sum(len(d["controls"]) for d in data["domains"])
    assert total_controls == 41


def test_cno1960_controls_carry_requirements_unlike_iso(client):
    """A diferencia de ISO 27001 (texto licenciado, sin Requirement), el
    Acuerdo 1960 es texto regulatorio público — su seed sí carga la tabla
    ``requirements`` con cada ítem de evidencia del Anexo 3."""
    resp = client.get("/api/v1/frameworks/CNO-1960/domains")
    domains = resp.json()
    control_id = next(d for d in domains if d["code"] == "5")["controls"][0]["id"]

    resp = client.get(f"/api/v1/controls/{control_id}")
    assert resp.status_code == 200
    assert len(resp.json()["requirements"]) >= 1
