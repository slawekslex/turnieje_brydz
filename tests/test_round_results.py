"""
Unit tests for round results view and cumulative ranking (round_results_view_data, round_ranking_data).
"""

import unittest
from datetime import date

from bridge.models.round_models import (
    Deal,
    Result,
    Round,
    TableAssignment,
    Team,
    TeamMember,
)
from bridge.models.tournament import Tournament
from bridge.services.round_results import round_head_to_head_data, round_ranking_data, round_results_view_data


def _make_teams(n: int):
    return [
        Team(
            id=i,
            name=f"Team {i}",
            member1=TeamMember(f"P{i}A"),
            member2=TeamMember(f"P{i}B"),
        )
        for i in range(1, n + 1)
    ]


def _make_deal(deal_id: int) -> Deal:
    return Deal(id=deal_id, box=1)


class TestRoundResultsViewData(unittest.TestCase):
    def test_round_not_found(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, deals_out = round_results_view_data(tournament, 999)
        self.assertIsNone(rnd_out)
        self.assertIsNone(deals_out)

    def test_round_with_no_results_has_none_imps(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, deals_out = round_results_view_data(tournament, 1)
        self.assertIsNotNone(rnd_out)
        self.assertEqual(len(deals_out), 1)
        rows = deals_out[0]["table_rows"]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].get("ns_imp"))
        self.assertIsNone(rows[0].get("ew_imp"))

    def test_round_with_one_table_full_result_has_imps(self):
        teams = _make_teams(2)
        res = Result(
            round_id=1,
            table_number=1,
            deal_id=1,
            ns_score=120,
            ew_score=0,
            contract="3NT",
            declarer="N",
            opening_lead="",
            tricks_taken=9,
        )
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={(1, 1): res},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, deals_out = round_results_view_data(tournament, 1)
        self.assertIsNotNone(rnd_out)
        rows = deals_out[0]["table_rows"]
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].get("ns_imp"))
        self.assertIsNotNone(rows[0].get("ew_imp"))
        self.assertEqual(rows[0]["ns_team"], "Team 1")
        self.assertEqual(rows[0]["ew_team"], "Team 2")

    def test_two_tables_different_scores_produce_non_zero_imps(self):
        teams = _make_teams(4)
        # Two tables, same deal: table1 NS=120, table2 NS=0 -> datum 60, diff ±60 -> IMP 2
        rnd = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(1, 1, 2),
                TableAssignment(2, 3, 4),
            ],
            deals=[_make_deal(1)],
            results_by_table_deal={
                (1, 1): Result(1, 1, 1, 120, 0, "3NT", "N", "", 9),
                (2, 1): Result(1, 2, 1, 0, 120, "3NT", "S", "", 9),
            },
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        _, deals_out = round_results_view_data(tournament, 1)
        rows = deals_out[0]["table_rows"]
        self.assertEqual(len(rows), 2)
        # Team 1 NS +IMP, Team 2 EW -IMP; Team 3 NS -IMP, Team 4 EW +IMP
        imp_by_team = {}
        for r in rows:
            imp_by_team[r["ns_team"]] = r["ns_imp"]
            imp_by_team[r["ew_team"]] = r["ew_imp"]
        self.assertEqual(imp_by_team["Team 1"], 2)
        self.assertEqual(imp_by_team["Team 2"], -2)
        self.assertEqual(imp_by_team["Team 3"], -2)
        self.assertEqual(imp_by_team["Team 4"], 2)


class TestRoundRankingData(unittest.TestCase):
    def test_round_not_found(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, ranking, round_nums, err = round_ranking_data(tournament, 999)
        self.assertIsNone(rnd_out)
        self.assertIsNone(ranking)
        self.assertEqual(err, "Runda nie znaleziona")

    def test_incomplete_results_returns_error(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, ranking, round_nums, err = round_ranking_data(tournament, 1)
        self.assertIsNotNone(rnd_out)
        self.assertIsNone(ranking)
        self.assertIn("Nie wszystkie wyniki są zapisane", err)
        self.assertIn("1", err)

    def test_single_round_full_results_returns_ranking(self):
        teams = _make_teams(2)
        res = Result(1, 1, 1, 120, 0, "3NT", "N", "", 9)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={(1, 1): res},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, ranking, round_nums, err = round_ranking_data(tournament, 1)
        self.assertIsNone(err)
        self.assertEqual(round_nums, [1])
        self.assertEqual(len(ranking), 2)
        names = [r["team_name"] for r in ranking]
        self.assertIn("Team 1", names)
        self.assertIn("Team 2", names)
        for r in ranking:
            self.assertIn("round_imps", r)
            self.assertEqual(len(r["round_imps"]), 1)
        # Single table: datum = 120, diff = 0, so both IMP 0
        totals = {r["team_name"]: r["total_imp"] for r in ranking}
        self.assertEqual(totals["Team 1"], 0)
        self.assertEqual(totals["Team 2"], 0)

    def test_cumulative_ranking_includes_lower_rounds(self):
        teams = _make_teams(4)
        # Round 1: two tables, datum 60 -> Team1/Team2 get +2/-2, Team3/Team4 get -2/+2
        r1 = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(1, 1, 2),
                TableAssignment(2, 3, 4),
            ],
            deals=[_make_deal(1)],
            results_by_table_deal={
                (1, 1): Result(1, 1, 1, 120, 0, "3NT", "N", "", 9),
                (2, 1): Result(1, 2, 1, 0, 120, "3NT", "S", "", 9),
            },
        )
        # Round 2: reverse so Team1/2 get -2/+2 and Team3/4 get +2/-2; cumulative cancels
        r2 = Round(
            id=2,
            round_number=2,
            tables=[
                TableAssignment(1, 1, 4),
                TableAssignment(2, 2, 3),
            ],
            deals=[_make_deal(2)],
            results_by_table_deal={
                (1, 2): Result(2, 1, 2, 0, 120, "3NT", "S", "", 9),
                (2, 2): Result(2, 2, 2, 120, 0, "3NT", "N", "", 9),
            },
        )
        tournament = Tournament("T", date.today(), teams, [r1, r2])

        # Ranking after round 1 only
        _, rank1, rn1, err = round_ranking_data(tournament, 1)
        self.assertIsNone(err)
        self.assertEqual(rn1, [1])
        totals1 = {r["team_name"]: r["total_imp"] for r in rank1}
        self.assertEqual(totals1["Team 1"], 2)
        self.assertEqual(totals1["Team 2"], -2)
        self.assertEqual(totals1["Team 3"], -2)
        self.assertEqual(totals1["Team 4"], 2)

        # Ranking after rounds 1 and 2 (cumulative): round2 table assignements differ
        # so totals are Team1 0, Team2 0, Team3 -4, Team4 +4
        _, rank2, rn2, err = round_ranking_data(tournament, 2)
        self.assertIsNone(err)
        self.assertEqual(rn2, [1, 2])
        for r in rank2:
            self.assertEqual(len(r["round_imps"]), 2)
        totals2 = {r["team_name"]: r["total_imp"] for r in rank2}
        self.assertEqual(totals2["Team 1"], 0)
        self.assertEqual(totals2["Team 2"], 0)
        self.assertEqual(totals2["Team 3"], -4)
        self.assertEqual(totals2["Team 4"], 4)
        self.assertEqual(len(rank2), 4)
        self.assertEqual(rank2[0]["team_name"], "Team 4")
        self.assertEqual(rank2[0]["total_imp"], 4)

    def test_ranking_sorted_by_total_imp_descending(self):
        teams = _make_teams(4)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(1, 1, 2),
                TableAssignment(2, 3, 4),
            ],
            deals=[_make_deal(1)],
            results_by_table_deal={
                (1, 1): Result(1, 1, 1, 120, 0, "3NT", "N", "", 9),
                (2, 1): Result(1, 2, 1, 0, 120, "3NT", "S", "", 9),
            },
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        _, ranking, _, _ = round_ranking_data(tournament, 1)
        imps = [r["total_imp"] for r in ranking]
        self.assertEqual(imps, sorted(imps, reverse=True))


class TestRoundHeadToHeadData(unittest.TestCase):
    def test_round_not_found(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, err, names, matrix = round_head_to_head_data(tournament, 999)
        self.assertIsNone(rnd_out)
        self.assertEqual(err, "Runda nie znaleziona")
        self.assertEqual(names, [])
        self.assertEqual(matrix, [])

    def test_incomplete_results_returns_error(self):
        teams = _make_teams(2)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(1, 1, 2)],
            deals=[_make_deal(1)],
            results_by_table_deal={},
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, err, names, matrix = round_head_to_head_data(tournament, 1)
        self.assertIsNotNone(rnd_out)
        self.assertIn("Nie wszystkie wyniki są zapisane", err)
        self.assertEqual(names, [])
        self.assertEqual(matrix, [])

    def test_single_round_two_tables_gives_h2h_matrix(self):
        teams = _make_teams(4)
        rnd = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(1, 1, 2),
                TableAssignment(2, 3, 4),
            ],
            deals=[_make_deal(1)],
            results_by_table_deal={
                (1, 1): Result(1, 1, 1, 120, 0, "3NT", "N", "", 9),
                (2, 1): Result(1, 2, 1, 0, 120, "3NT", "S", "", 9),
            },
        )
        tournament = Tournament("T", date.today(), teams, [rnd])
        rnd_out, err, team_names, matrix = round_head_to_head_data(tournament, 1)
        self.assertIsNone(err)
        self.assertEqual(sorted(team_names), ["Team 1", "Team 2", "Team 3", "Team 4"])
        idx = {n: i for i, n in enumerate(team_names)}
        # Team 1 vs Team 2: Team 1 (NS) +2, Team 2 (EW) -2
        self.assertEqual(matrix[idx["Team 1"]][idx["Team 2"]], 2)
        self.assertEqual(matrix[idx["Team 2"]][idx["Team 1"]], -2)
        # Team 3 vs Team 4: Team 3 (NS) -2, Team 4 (EW) +2
        self.assertEqual(matrix[idx["Team 3"]][idx["Team 4"]], -2)
        self.assertEqual(matrix[idx["Team 4"]][idx["Team 3"]], 2)
        # Diagonals 0
        for i in range(4):
            self.assertEqual(matrix[i][i], 0)
