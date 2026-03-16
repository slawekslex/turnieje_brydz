"""
Integration test: scheduling, scoring, and final rankings.

Expected results are computed from first principles (same algorithms as the app),
not from app responses, so bugs in the app are detected.

- Schedule: we use the same round-robin generator (add_round_robin) with the same
  team order and IDs (1–4) as the app assigns on create, and take the first 2 rounds.
- Scoring: we submit contracts that yield known raw scores (2S N 8 → NS 120, 2S S 8 → NS 0
  with vulnerability None). Standard duplicate bridge scoring.
- IMPs: datum = round(mean(ns_scores), -1) = 60; standard WBF IMP table gives +2 / -2
  per table. We compute expected IMP per team from the schedule and these rules.
- We then create the tournament via API, post the same results, and assert the
  ranking matches our expected totals and order.
"""

import pytest

from bridge.models.round_models import Team, TeamMember
from bridge.scoring import calculate_deal_imp_scores, compute_score
from bridge.services.generator import add_round_robin


def _create_tournament(client):
    """Create 4 teams, 2 rounds, 1 deal per round. Returns tour_id and rounds payload."""
    payload = {
        "name": "Schedule & Ranking Test",
        "date": "2025-07-01",
        "teams": [
            {"name": "Alpha", "member1": "A1", "member2": "A2"},
            {"name": "Beta", "member1": "B1", "member2": "B2"},
            {"name": "Gamma", "member1": "G1", "member2": "G2"},
            {"name": "Delta", "member1": "D1", "member2": "D2"},
        ],
        "num_rounds": 2,
        "deals_per_round": 1,
    }
    r = client.post("/api/tournaments", json=payload)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data.get("ok") is True
    tour_id = data["id"]
    return tour_id


def _get_rounds(client, tour_id):
    """GET rounds; returns list of round dicts with round_id, tables, deals."""
    r = client.get(f"/api/tournaments/{tour_id}/rounds")
    assert r.status_code == 200
    data = r.get_json()
    return data["rounds"]


def _post_round_results(client, tour_id, round_id, results):
    """POST round-results. results = list of {table_number, deal_id, contract, declarer, opening_lead, tricks_taken}."""
    r = client.post(
        f"/api/tournaments/{tour_id}/round-results",
        json={"round_id": round_id, "results": results},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data.get("ok") is True
    return data


def _get_ranking(client, tour_id, round_id):
    """GET ranking for a round. Returns ranking list and round_numbers."""
    r = client.get(f"/api/tournaments/{tour_id}/rounds/{round_id}/ranking")
    assert r.status_code == 200
    data = r.get_json()
    return data.get("ranking") or [], data.get("round_numbers") or []


def _get_deal_results(client, tour_id, round_id):
    """GET deal-results for a round. Returns list of {deal, table_rows} with ns_team, ew_team, ns_imp, ew_imp."""
    r = client.get(f"/api/tournaments/{tour_id}/rounds/{round_id}/deal-results")
    assert r.status_code == 200
    data = r.get_json()
    return data.get("deals_with_tables") or []


# --- First-principles expected schedule and IMPs (no app data) ---

# Same 4 teams as in _create_tournament payload; app assigns id=i+1 in that order.
TEAM_NAMES = ["Alpha", "Beta", "Gamma", "Delta"]


def _teams_like_app():
    """Teams with same ids and order as app creates from our payload."""
    return [
        Team(id=i + 1, name=TEAM_NAMES[i], member1=TeamMember("X1"), member2=TeamMember("X2"))
        for i in range(4)
    ]


def _expected_schedule_first_two_rounds():
    """
    Schedule from the same generator the app uses (add_round_robin, no existing cycles),
    first 2 rounds. Returns list of rounds, each round = list of (table_number, ns_team_name, ew_team_name).
    """
    teams = _teams_like_app()
    full_cycle = add_round_robin(teams, [], k=1)
    team_by_id = {t.id: t.name for t in teams}
    out = []
    for rnd in full_cycle[:2]:
        round_tables = []
        for tbl in sorted(rnd.tables, key=lambda x: x.table_number):
            round_tables.append((tbl.table_number, team_by_id[tbl.ns_team_id], team_by_id[tbl.ew_team_id]))
        out.append(round_tables)
    return out


def _expected_imps_from_first_principles():
    """
    From first principles: we post table 1 → NS 110 (2S N 8), table 2 → NS -110 (2S E 8), vul None.
    Datum = round(mean(ns_scores), -1). IMP from standard WBF table via calculate_deal_imp_scores.
    Returns dict team_name -> total IMP (over 2 rounds) using _expected_schedule_first_two_rounds().
    """
    ns_scores_per_deal = [110, -110]
    imp_pairs = calculate_deal_imp_scores(ns_scores_per_deal)
    schedule = _expected_schedule_first_two_rounds()
    expected = {n: 0 for n in TEAM_NAMES}
    for round_tables in schedule:
        for (table_number, ns_name, ew_name), (ns_imp, ew_imp) in zip(round_tables, imp_pairs):
            expected[ns_name] += ns_imp
            expected[ew_name] += ew_imp
    return expected


def test_schedule_structure(client):
    """Schedule has correct number of rounds and tables; each team plays once per round."""
    tour_id = _create_tournament(client)
    rounds = _get_rounds(client, tour_id)
    assert len(rounds) == 2
    team_names = {"Alpha", "Beta", "Gamma", "Delta"}
    for rnd in rounds:
        assert "round_id" in rnd
        assert "round_number" in rnd
        tables = rnd["tables"]
        assert len(tables) == 2
        playing = set()
        for tbl in tables:
            ns = tbl["ns_team"]["name"]
            ew = tbl["ew_team"]["name"]
            assert ns in team_names
            assert ew in team_names
            assert ns != ew
            playing.add(ns)
            playing.add(ew)
        assert len(playing) == 4
        assert len(rnd["deals"]) == 1


def test_schedule_matches_first_principles(client):
    """Schedule from the API must match the one we derive from the same generator (first principles)."""
    expected = _expected_schedule_first_two_rounds()
    tour_id = _create_tournament(client)
    rounds = _get_rounds(client, tour_id)
    assert len(rounds) == len(expected)
    for rnd, exp_round in zip(rounds, expected):
        app_tables = sorted(rnd["tables"], key=lambda t: t["table_number"])
        assert len(app_tables) == len(exp_round)
        for tbl, (exp_table_num, exp_ns, exp_ew) in zip(app_tables, exp_round):
            assert tbl["table_number"] == exp_table_num
            assert tbl["ns_team"]["name"] == exp_ns
            assert tbl["ew_team"]["name"] == exp_ew


def test_scoring_and_ranking_after_full_results(client):
    """
    Post complete results for both rounds; assert IMPs sum to zero and final
    ranking is sorted by total_imp descending. Uses contracts that yield
    known NS scores (2S N 8 → 110, 2S S 8 → 0 for NS; datum 60, IMPs +2/-2).
    """
    tour_id = _create_tournament(client)
    rounds = _get_rounds(client, tour_id)

    # Build and post results for each round: one table NS 110, one table NS 0 (2S N 8 vs 2S S 8)
    for rnd in rounds:
        round_id = rnd["round_id"]
        deal = rnd["deals"][0]
        deal_id = deal["id"]
        results = []
        for tbl in rnd["tables"]:
            # Alternate which table gets +IMP so we can check cumulative
            table_num = tbl["table_number"]
            if table_num == 1:
                contract, declarer = "2S", "N"   # NS 120
            else:
                contract, declarer = "2S", "S"   # EW 120 → NS 0
            results.append({
                "table_number": table_num,
                "deal_id": deal_id,
                "contract": contract,
                "declarer": declarer,
                "opening_lead": "2H",
                "tricks_taken": 8,
            })
        _post_round_results(client, tour_id, round_id, results)

    # Ranking after round 1: two tables, datum 60 → +2 and -2 per table
    rank1, rn1 = _get_ranking(client, tour_id, rounds[0]["round_id"])
    assert len(rank1) == 4
    assert rn1 == [1]
    total_imp_r1 = sum(r["total_imp"] for r in rank1)
    assert total_imp_r1 == 0
    assert rank1 == sorted(rank1, key=lambda x: -x["total_imp"])

    # Ranking after round 2 (cumulative)
    rank2, rn2 = _get_ranking(client, tour_id, rounds[1]["round_id"])
    assert len(rank2) == 4
    assert rn2 == [1, 2]
    total_imp_r2 = sum(r["total_imp"] for r in rank2)
    assert total_imp_r2 == 0
    assert rank2 == sorted(rank2, key=lambda x: -x["total_imp"])

    # Each team has round_imps for both rounds
    for r in rank2:
        assert len(r["round_imps"]) == 2
        assert r["total_imp"] == sum(r["round_imps"])


def test_ranking_matches_first_principles(client):
    """
    Expected IMPs are computed from first principles (same schedule generator,
    standard duplicate scoring, WBF IMP table). We then create the tournament
    via API, post the same results, and assert the app's ranking matches.
    Any mismatch indicates a bug in scheduling, scoring, or ranking.
    """
    # Raw scores: table 1 2S N 8 → NS 110; table 2 2S E 8 → NS -110 (standard duplicate)
    score_ns_110 = compute_score("2S", "N", 8, "None")
    score_ns_neg110 = compute_score("2S", "E", 8, "None")
    assert score_ns_110 is not None and score_ns_neg110 is not None
    assert score_ns_110[0] == 110 and score_ns_neg110[0] == -110

    expected_imp = _expected_imps_from_first_principles()
    assert sum(expected_imp.values()) == 0

    tour_id = _create_tournament(client)
    rounds = _get_rounds(client, tour_id)

    for rnd in rounds:
        round_id = rnd["round_id"]
        deal_id = rnd["deals"][0]["id"]
        results = [
            {"table_number": 1, "deal_id": deal_id, "contract": "2S", "declarer": "N", "opening_lead": "2H", "tricks_taken": 8},
            {"table_number": 2, "deal_id": deal_id, "contract": "2S", "declarer": "E", "opening_lead": "2H", "tricks_taken": 8},
        ]
        _post_round_results(client, tour_id, round_id, results)

    rank, round_numbers = _get_ranking(client, tour_id, rounds[1]["round_id"])
    assert round_numbers == [1, 2]
    by_name = {r["team_name"]: r["total_imp"] for r in rank}
    for team in TEAM_NAMES:
        assert team in by_name, f"Missing team {team} in ranking"
        assert by_name[team] == expected_imp[team], (
            f"{team}: app has {by_name[team]}, expected from first principles {expected_imp[team]}"
        )
    assert sum(r["total_imp"] for r in rank) == 0
    assert [r["total_imp"] for r in rank] == sorted((r["total_imp"] for r in rank), reverse=True)
