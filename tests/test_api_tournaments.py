"""
API tests using Flask test client.
Covers: list tournaments, create, get, archive, round-results, ranking.
Uses a directory under tests/ for DATA_DIR so real data is not touched.
"""

import shutil
from pathlib import Path

import pytest

# Directory under tests/ for API test data (gitignored)
TESTS_API_DATA_DIR = Path(__file__).resolve().parent / "tmp_api_tournaments"


@pytest.fixture
def client():
    """Flask test client with DATA_DIR set to tests/tmp_api_tournaments (cleaned each run)."""
    import app as app_module
    from bridge.storage import ensure_data_dir

    data_dir = TESTS_API_DATA_DIR
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    ensure_data_dir(data_dir)
    original_data_dir = app_module.app.config["DATA_DIR"]
    app_module.app.config["DATA_DIR"] = data_dir
    app_module.app.config["TESTING"] = True
    try:
        yield app_module.app.test_client()
    finally:
        app_module.app.config["DATA_DIR"] = original_data_dir
        shutil.rmtree(data_dir, ignore_errors=True)


def test_list_tournaments_empty(client):
    r = client.get("/api/tournaments")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_create_tournament(client):
    payload = {
        "name": "Test Cup",
        "date": "2025-06-01",
        "teams": [
            {"name": "A", "member1": "A1", "member2": "A2"},
            {"name": "B", "member1": "B1", "member2": "B2"},
        ],
        "num_rounds": 1,
        "deals_per_round": 1,
    }
    r = client.post("/api/tournaments", json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("ok") is True
    assert "id" in data
    assert data.get("name") == "Test Cup"
    assert data.get("date") == "2025-06-01"


def test_list_tournaments_after_create(client):
    payload = {
        "name": "List Test",
        "date": "2025-07-01",
        "teams": [
            {"name": "X", "member1": "X1", "member2": "X2"},
            {"name": "Y", "member1": "Y1", "member2": "Y2"},
        ],
        "num_rounds": 1,
        "deals_per_round": 1,
    }
    client.post("/api/tournaments", json=payload)
    r = client.get("/api/tournaments")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "List Test"
    assert "id" in data[0]


def test_get_tournament(client):
    payload = {
        "name": "Get Test",
        "date": "2025-08-01",
        "teams": [
            {"name": "T1", "member1": "M1a", "member2": "M1b"},
            {"name": "T2", "member1": "M2a", "member2": "M2b"},
        ],
        "num_rounds": 1,
        "deals_per_round": 1,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    r = client.get(f"/api/tournaments/{tour_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Get Test"
    assert data["date"] == "2025-08-01"
    assert len(data["teams"]) == 2
    assert data["teams"][0]["name"] == "T1"
    assert "cycles" in data


def test_get_tournament_404(client):
    r = client.get("/api/tournaments/nonexistent-id-12345")
    assert r.status_code == 404
    data = r.get_json()
    assert "error" in data


def test_get_tournament_rounds(client):
    payload = {
        "name": "Rounds Test",
        "date": "2025-09-01",
        "teams": [
            {"name": "P", "member1": "P1", "member2": "P2"},
            {"name": "Q", "member1": "Q1", "member2": "Q2"},
        ],
        "num_rounds": 1,
        "deals_per_round": 2,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    r = client.get(f"/api/tournaments/{tour_id}/rounds")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Rounds Test"
    assert len(data["rounds"]) == 1
    rnd = data["rounds"][0]
    assert rnd["round_number"] == 1
    assert "round_id" in rnd
    assert len(rnd["deals"]) == 2
    assert len(rnd["tables"]) == 1


def test_archive_tournament(client):
    payload = {
        "name": "Archive Test",
        "date": "2025-10-01",
        "teams": [
            {"name": "U", "member1": "U1", "member2": "U2"},
            {"name": "V", "member1": "V1", "member2": "V2"},
        ],
        "num_rounds": 1,
        "deals_per_round": 1,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    r = client.post(f"/api/tournaments/{tour_id}/archive")
    assert r.status_code == 200
    assert r.get_json().get("ok") is True
    list_r = client.get("/api/tournaments")
    assert list_r.status_code == 200
    active = list_r.get_json()
    assert len(active) == 0


def test_save_round_results(client):
    payload = {
        "name": "Results Test",
        "date": "2025-11-01",
        "teams": [
            {"name": "NS", "member1": "N1", "member2": "N2"},
            {"name": "EW", "member1": "E1", "member2": "E2"},
        ],
        "num_rounds": 1,
        "deals_per_round": 2,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    rounds_r = client.get(f"/api/tournaments/{tour_id}/rounds")
    rounds_data = rounds_r.get_json()
    rnd = rounds_data["rounds"][0]
    round_id = rnd["round_id"]
    deals = rnd["deals"]
    tables = rnd["tables"]
    results = []
    for t in tables:
        for d in deals:
            results.append({
                "table_number": t["table_number"],
                "deal_id": d["id"],
                "contract": "1NT",
                "declarer": "N",
                "opening_lead": "2H",
                "tricks_taken": 7,
            })
    save_r = client.post(
        f"/api/tournaments/{tour_id}/round-results",
        json={"round_id": round_id, "results": results},
    )
    assert save_r.status_code == 200
    save_data = save_r.get_json()
    assert save_data.get("ok") is True
    assert save_data.get("saved") == len(results)
    assert save_data.get("total") == len(results)


def test_round_ranking_after_save(client):
    payload = {
        "name": "Ranking Test",
        "date": "2025-12-01",
        "teams": [
            {"name": "Team1", "member1": "a", "member2": "b"},
            {"name": "Team2", "member1": "c", "member2": "d"},
        ],
        "num_rounds": 1,
        "deals_per_round": 2,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    rounds_r = client.get(f"/api/tournaments/{tour_id}/rounds")
    rnd = rounds_r.get_json()["rounds"][0]
    round_id = rnd["round_id"]
    results = []
    for t in rnd["tables"]:
        for d in rnd["deals"]:
            results.append({
                "table_number": t["table_number"],
                "deal_id": d["id"],
                "contract": "2S",
                "declarer": "S",
                "opening_lead": "3C",
                "tricks_taken": 8,
            })
    client.post(
        f"/api/tournaments/{tour_id}/round-results",
        json={"round_id": round_id, "results": results},
    )
    rank_r = client.get(f"/api/tournaments/{tour_id}/rounds/{round_id}/ranking")
    assert rank_r.status_code == 200
    rank_data = rank_r.get_json()
    assert "round_number" in rank_data
    assert "ranking" in rank_data
    assert len(rank_data["ranking"]) == 2
    assert "team_name" in rank_data["ranking"][0]
    assert "total_imp" in rank_data["ranking"][0]
    assert "round_imps" in rank_data["ranking"][0]


def test_create_tournament_validation_errors(client):
    r = client.post("/api/tournaments", json={"name": "", "date": "2025-01-01", "teams": []})
    assert r.status_code == 400
    data = r.get_json()
    assert data.get("ok") is False
    assert "errors" in data
    assert len(data["errors"]) > 0


def test_round_results_400_missing_round_id(client):
    payload = {
        "name": "R",
        "date": "2025-01-01",
        "teams": [
            {"name": "A", "member1": "a", "member2": "b"},
            {"name": "B", "member1": "c", "member2": "d"},
        ],
        "num_rounds": 1,
        "deals_per_round": 1,
    }
    cr = client.post("/api/tournaments", json=payload)
    tour_id = cr.get_json()["id"]
    r = client.post(
        f"/api/tournaments/{tour_id}/round-results",
        json={"results": []},
    )
    assert r.status_code == 400
    assert "error" in r.get_json()
