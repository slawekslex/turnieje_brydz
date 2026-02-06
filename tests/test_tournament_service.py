"""Tests for tournament_service (parse_tournament_payload, duplicate team names)."""
import unittest
from datetime import date

from bridge.services.tournament_service import parse_tournament_payload


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
