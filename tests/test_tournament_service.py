"""Tests for tournament_service (parse_tournament_payload, duplicate team names)."""
import unittest
from datetime import date

from bridge.models.round_models import Deal, Result, Round, TableAssignment, Team, TeamMember
from bridge.models.tournament import Tournament
from bridge.services.tournament_service import apply_non_breaking_update, parse_tournament_payload


class ParseTournamentPayloadTests(unittest.TestCase):
    def test_duplicate_team_names_rejected(self) -> None:
        body = {
            "name": "Test",
            "date": "2025-06-01",
            "teams": [
                {"name": "Alfa", "member1": "A1", "member2": "A2"},
                {"name": "Alfa", "member1": "B1", "member2": "B2"},
            ],
        }
        data, errors = parse_tournament_payload(body)
        self.assertIsNone(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("Alfa", errors[0])
        self.assertIn("tę samą nazwę", errors[0])

    def test_multiple_duplicate_names_listed(self) -> None:
        body = {
            "name": "Test",
            "date": "2025-06-01",
            "teams": [
                {"name": "X", "member1": "a", "member2": "b"},
                {"name": "Y", "member1": "c", "member2": "d"},
                {"name": "X", "member1": "e", "member2": "f"},
                {"name": "Y", "member1": "g", "member2": "h"},
            ],
        }
        data, errors = parse_tournament_payload(body)
        self.assertIsNone(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("X", errors[0])
        self.assertIn("Y", errors[0])

    def test_unique_team_names_accepted(self) -> None:
        body = {
            "name": "Test",
            "date": "2025-06-01",
            "teams": [
                {"name": "Alfa", "member1": "A1", "member2": "A2"},
                {"name": "Beta", "member1": "B1", "member2": "B2"},
            ],
        }
        data, errors = parse_tournament_payload(body)
        self.assertEqual(errors, [])
        self.assertIsNotNone(data)
        name, tournament_date, teams, cycles, rounds = data
        self.assertEqual(name, "Test")
        self.assertEqual(tournament_date, date(2025, 6, 1))
        self.assertEqual([t.name for t in teams], ["Alfa", "Beta"])

    def test_odd_number_of_teams_accepted(self) -> None:
        """Odd number of teams is accepted (one bye per round)."""
        body = {
            "name": "Three Teams",
            "date": "2025-07-01",
            "teams": [
                {"name": "A", "member1": "A1", "member2": "A2"},
                {"name": "B", "member1": "B1", "member2": "B2"},
                {"name": "C", "member1": "C1", "member2": "C2"},
            ],
            "num_rounds": 3,
            "deals_per_round": 2,
        }
        data, errors = parse_tournament_payload(body)
        self.assertEqual(errors, [])
        self.assertIsNotNone(data)
        name, tournament_date, teams, cycles, rounds = data
        self.assertEqual(len(teams), 3)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(rounds), 3)

    def test_default_number_of_boxes_is_16(self) -> None:
        body = {
            "name": "Default Boxes",
            "date": "2025-06-01",
            "teams": [
                {"name": "Alfa", "member1": "A1", "member2": "A2"},
                {"name": "Beta", "member1": "B1", "member2": "B2"},
            ],
            "num_rounds": 1,
            "deals_per_round": 2,
        }
        data, errors = parse_tournament_payload(body)
        self.assertEqual(errors, [])
        self.assertIsNotNone(data)
        _, _, _, _, rounds = data
        # deal ids 1,2 should map to boxes 1,2 when default boxes=16
        self.assertEqual([d.box for d in rounds[0].deals], [1, 2])


class ApplyNonBreakingUpdateBoxesTests(unittest.TestCase):
    def test_box_count_change_updates_only_unplayed_rounds(self) -> None:
        teams = [
            Team(id=1, name="A", member1=TeamMember("A1"), member2=TeamMember("A2")),
            Team(id=2, name="B", member1=TeamMember("B1"), member2=TeamMember("B2")),
        ]
        played_round = Round(
            id=1,
            round_number=1,
            tables=[TableAssignment(table_number=1, ns_team_id=1, ew_team_id=2)],
            deals=[Deal(id=1, box=1)],
            results_by_table_deal={
                (1, 1): Result(
                    round_id=1,
                    table_number=1,
                    deal_id=1,
                    ns_score=90,
                    ew_score=-90,
                )
            },
        )
        unplayed_round = Round(
            id=2,
            round_number=2,
            tables=[TableAssignment(table_number=1, ns_team_id=2, ew_team_id=1)],
            deals=[Deal(id=2, box=1)],
            results_by_table_deal={},
        )
        existing = Tournament(
            name="Test",
            date=date(2025, 6, 1),
            teams=teams,
            rounds=[played_round, unplayed_round],
            number_of_boxes=1,
        )

        updated = apply_non_breaking_update(
            existing=existing,
            name=existing.name,
            tournament_date=existing.date,
            teams=teams,
            new_num_rounds=2,
            new_cycles=[{"deals_per_round": 1}],
            number_of_boxes=4,
        )

        self.assertEqual(updated.number_of_boxes, 4)
        self.assertEqual(updated.rounds[0].deals[0].box, 1)  # played round unchanged
        self.assertEqual(updated.rounds[1].deals[0].box, 2)  # unplayed round remapped
