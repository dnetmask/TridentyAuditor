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
