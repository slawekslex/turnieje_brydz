"""Tests for schedule_view_data (schedule page data)."""
import unittest
from datetime import date

from bridge.models.round_models import Team, TeamMember
from bridge.models.tournament import Tournament
from bridge.services.generator import generate_round_robin
from bridge.services.schedule import schedule_view_data


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


class ScheduleViewDataTests(unittest.TestCase):
    def test_returns_one_entry_per_round(self):
        teams = _make_teams(4)
        rounds = generate_round_robin(teams)
        tournament = Tournament(name="T", date=date(2025, 1, 1), teams=teams, rounds=rounds)
        schedule = schedule_view_data(tournament)
        self.assertEqual(len(schedule), len(rounds))
        for i, item in enumerate(schedule):
            self.assertEqual(item["round_number"], rounds[i].round_number)
            self.assertEqual(len(item["tables"]), 2)

    def test_tables_have_ns_ew_names(self):
        teams = _make_teams(4)
        rounds = generate_round_robin(teams)
        tournament = Tournament(name="T", date=date(2025, 1, 1), teams=teams, rounds=rounds)
        schedule = schedule_view_data(tournament)
        self.assertGreater(len(schedule), 0)
        for round_data in schedule:
            for tbl in round_data["tables"]:
                self.assertIn("table_number", tbl)
                self.assertIn("ns_name", tbl)
                self.assertIn("ew_name", tbl)
                self.assertIsInstance(tbl["ns_name"], str)
                self.assertIsInstance(tbl["ew_name"], str)

    def test_empty_rounds_returns_empty_schedule(self):
        teams = _make_teams(2)
        tournament = Tournament(name="T", date=date(2025, 1, 1), teams=teams, rounds=[])
        schedule = schedule_view_data(tournament)
        self.assertEqual(schedule, [])

    def test_round_with_bye_includes_byes_list(self):
        """With odd number of teams, each round has one team with bye; schedule shows it."""
        teams = _make_teams(3)
        rounds = generate_round_robin(teams)
        tournament = Tournament(name="T", date=date(2025, 1, 1), teams=teams, rounds=rounds)
        schedule = schedule_view_data(tournament)
        self.assertEqual(len(schedule), 3)
        for round_data in schedule:
            self.assertIn("byes", round_data)
            self.assertEqual(len(round_data["byes"]), 1)
            self.assertIn("team_name", round_data["byes"][0])
            self.assertIn(round_data["byes"][0]["team_name"], ["Team 1", "Team 2", "Team 3"])
