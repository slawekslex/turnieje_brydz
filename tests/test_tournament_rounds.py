"""
Unit and integration tests for tournament rounds/cycles: creating rounds from
num_rounds + deals_per_round, correct cycles in storage, and (via API) updating
round count.
"""

import json
import unittest
from pathlib import Path

from bridge.models.round_models import Team, TeamMember
from bridge.services.generator import validate_round_robin
from bridge.storage import get_tournament_data_path


def _make_teams(n: int) -> list:
    return [
        Team(
            id=i,
            name=f"Team {i}",
            member1=TeamMember(f"Player {i}A"),
            member2=TeamMember(f"Player {i}B"),
        )
        for i in range(1, n + 1)
    ]


class TestCyclesFromNumRounds(unittest.TestCase):
    """Test _cycles_from_num_rounds_and_deals and rounds built from those cycles."""

    def test_cycles_from_num_rounds_one_cycle(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        # 4 teams -> 3 rounds per cycle. 3 rounds -> 1 cycle.
        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=4, num_rounds=3, deals_per_round=2
        )
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["deals_per_round"], 2)

        teams = _make_teams(4)
        rounds = _build_rounds_from_cycles(teams, cycles)
        self.assertEqual(len(rounds), 3)
        for rnd in rounds:
            self.assertEqual(len(rnd.tables), 2)
            self.assertEqual(len(rnd.deals), 2)
        validate_round_robin(teams, rounds)

    def test_cycles_from_num_rounds_two_cycles(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        # 4 teams -> 3 rounds per cycle. 6 rounds -> 2 cycles.
        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=4, num_rounds=6, deals_per_round=2
        )
        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0]["deals_per_round"], 2)
        self.assertEqual(cycles[1]["deals_per_round"], 2)

        teams = _make_teams(4)
        rounds = _build_rounds_from_cycles(teams, cycles)
        self.assertEqual(len(rounds), 6)
        for rnd in rounds:
            self.assertEqual(len(rnd.deals), 2)
        # Deal IDs sequential across all rounds: 1,2 per round -> 1,2, 3,4, 5,6, ...
        all_deal_ids = []
        for rnd in rounds:
            all_deal_ids.extend(d.id for d in rnd.deals)
        self.assertEqual(all_deal_ids, list(range(1, len(all_deal_ids) + 1)))

    def test_cycles_from_num_rounds_six_teams(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        # 6 teams -> 5 rounds per cycle. 10 rounds -> 2 cycles.
        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=6, num_rounds=10, deals_per_round=3
        )
        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0]["deals_per_round"], 3)

        teams = _make_teams(6)
        rounds = _build_rounds_from_cycles(teams, cycles)
        self.assertEqual(len(rounds), 10)
        for rnd in rounds:
            self.assertEqual(len(rnd.tables), 3)
            self.assertEqual(len(rnd.deals), 3)

    def test_cycles_from_num_rounds_zero_rounds(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=4, num_rounds=0, deals_per_round=2
        )
        self.assertEqual(cycles, [])

        # When cycles=[], _build_rounds_from_cycles uses a default single cycle,
        # so we get (teams-1) rounds. Caller (create_tournament) uses "if cycles else []"
        # to get 0 rounds when num_rounds=0; here we test the helper directly.
        teams = _make_teams(4)
        rounds = _build_rounds_from_cycles(teams, cycles)
        self.assertEqual(len(rounds), 3)  # default one cycle for 4 teams

    def test_round_ids_and_round_numbers_sequential(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=4, num_rounds=6, deals_per_round=1
        )
        teams = _make_teams(4)
        rounds = _build_rounds_from_cycles(teams, cycles)
        for i, rnd in enumerate(rounds):
            self.assertEqual(rnd.id, i + 1)
            self.assertEqual(rnd.round_number, i + 1)

    def test_cycles_partial_last_cycle(self) -> None:
        from bridge.api.routes import (
            _build_rounds_from_cycles,
            _cycles_from_num_rounds_and_deals,
        )

        # 4 teams -> 3 per cycle. 5 rounds = 1 full + 2 (partial)
        cycles = _cycles_from_num_rounds_and_deals(
            num_teams=4, num_rounds=5, deals_per_round=2
        )
        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0], {"deals_per_round": 2})
        self.assertEqual(cycles[1], {"deals_per_round": 2, "rounds": 2})

        teams = _make_teams(4)
        rounds = _build_rounds_from_cycles(teams, cycles)
        self.assertEqual(len(rounds), 5)
        for rnd in rounds:
            self.assertEqual(len(rnd.deals), 2)


class TestTournamentRoundsAPI(unittest.TestCase):
    """Integration tests: create/update tournament via API, assert cycles and rounds on disk."""

    def setUp(self) -> None:
        # Use a dir under tests so sandbox allows writes
        self.data_dir = Path(__file__).resolve().parent / "tmp_tournament_rounds_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        from app import app
        self.app = app
        self.app.config["DATA_DIR"] = self.data_dir
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        import shutil
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir, ignore_errors=True)

    def _create_tournament(self, num_rounds: int, deals_per_round: int = 2) -> dict:
        payload = {
            "name": "Test Cup",
            "date": "2025-06-01",
            "teams": [
                {"name": "A", "member1": "A1", "member2": "A2"},
                {"name": "B", "member1": "B1", "member2": "B2"},
                {"name": "C", "member1": "C1", "member2": "C2"},
                {"name": "D", "member1": "D1", "member2": "D2"},
            ],
            "num_rounds": num_rounds,
            "deals_per_round": deals_per_round,
        }
        r = self.client.post(
            "/api/tournaments",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        data = r.get_json()
        self.assertTrue(data.get("ok"))
        self.assertIn("id", data)
        return data

    def _load_tournament_file(self, tour_id: str) -> dict:
        path = get_tournament_data_path(self.data_dir, tour_id)
        self.assertIsNotNone(path, f"Tournament not found for {tour_id}")
        self.assertTrue(path.exists(), f"Tournament file not found for {tour_id}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def test_create_tournament_stores_correct_cycles_and_rounds(self) -> None:
        data = self._create_tournament(num_rounds=6, deals_per_round=2)
        tour_id = data["id"]
        stored = self._load_tournament_file(tour_id)

        # 4 teams -> 3 rounds per cycle. 6 rounds -> 2 cycles.
        cycles = stored.get("cycles", [])
        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0]["deals_per_round"], 2)
        self.assertEqual(cycles[1]["deals_per_round"], 2)

        rounds = stored.get("rounds", [])
        self.assertEqual(len(rounds), 6)
        for i, rnd in enumerate(rounds):
            self.assertEqual(rnd["round_number"], i + 1)
            self.assertEqual(rnd["id"], i + 1)
            self.assertEqual(len(rnd["deals"]), 2)

    def test_create_tournament_one_cycle(self) -> None:
        data = self._create_tournament(num_rounds=3, deals_per_round=3)
        stored = self._load_tournament_file(data["id"])
        self.assertEqual(len(stored["cycles"]), 1)
        self.assertEqual(len(stored["rounds"]), 3)
        for rnd in stored["rounds"]:
            self.assertEqual(len(rnd["deals"]), 3)

    def test_create_tournament_num_rounds_not_divisible_allowed_partial_cycle(self) -> None:
        # 4 teams -> 3 rounds per full cycle; 5 rounds = one full + 2 (partial last cycle)
        payload = {
            "name": "Partial",
            "date": "2025-06-01",
            "teams": [
                {"name": "A", "member1": "A1", "member2": "A2"},
                {"name": "B", "member1": "B1", "member2": "B2"},
                {"name": "C", "member1": "C1", "member2": "C2"},
                {"name": "D", "member1": "D1", "member2": "D2"},
            ],
            "num_rounds": 5,
            "deals_per_round": 2,
        }
        r = self.client.post(
            "/api/tournaments",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("ok"))
        stored = self._load_tournament_file(data["id"])
        self.assertEqual(len(stored["rounds"]), 5)
        self.assertEqual(len(stored["cycles"]), 2)
        self.assertEqual(stored["cycles"][0]["deals_per_round"], 2)
        self.assertEqual(stored["cycles"][1].get("rounds"), 2)

    def test_update_tournament_rebuilds_rounds_and_cycles(self) -> None:
        data = self._create_tournament(num_rounds=3, deals_per_round=2)
        tour_id = data["id"]

        # Update to 6 rounds (2 cycles)
        r = self.client.put(
            f"/api/tournaments/{tour_id}",
            data=json.dumps({
                "name": "Test Cup",
                "date": "2025-06-01",
                "teams": [
                    {"name": "A", "member1": "A1", "member2": "A2"},
                    {"name": "B", "member1": "B1", "member2": "B2"},
                    {"name": "C", "member1": "C1", "member2": "C2"},
                    {"name": "D", "member1": "D1", "member2": "D2"},
                ],
                "num_rounds": 6,
                "deals_per_round": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)

        stored = self._load_tournament_file(tour_id)
        self.assertEqual(len(stored["cycles"]), 2)
        self.assertEqual(len(stored["rounds"]), 6)

    def test_update_tournament_fewer_rounds_removes_rounds(self) -> None:
        data = self._create_tournament(num_rounds=6, deals_per_round=2)
        tour_id = data["id"]
        stored = self._load_tournament_file(tour_id)
        self.assertEqual(len(stored["rounds"]), 6)

        # Reduce to 3 rounds (1 cycle)
        r = self.client.put(
            f"/api/tournaments/{tour_id}",
            data=json.dumps({
                "name": "Test Cup",
                "date": "2025-06-01",
                "teams": [
                    {"name": "A", "member1": "A1", "member2": "A2"},
                    {"name": "B", "member1": "B1", "member2": "B2"},
                    {"name": "C", "member1": "C1", "member2": "C2"},
                    {"name": "D", "member1": "D1", "member2": "D2"},
                ],
                "num_rounds": 3,
                "deals_per_round": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)

        stored = self._load_tournament_file(tour_id)
        self.assertEqual(len(stored["cycles"]), 1)
        self.assertEqual(len(stored["rounds"]), 3)

    def test_update_in_progress_increase_num_rounds_appends_rounds(self) -> None:
        data = self._create_tournament(num_rounds=3, deals_per_round=2)
        tour_id = data["id"]
        stored = self._load_tournament_file(tour_id)
        round1 = stored["rounds"][0]
        table1 = round1["tables"][0]
        deal_id = round1["deals"][0]["id"]
        # Save one result so tournament is "in progress"
        r = self.client.post(
            f"/api/tournaments/{tour_id}/round-results",
            data=json.dumps({
                "round_id": 1,
                "results": [{
                    "table_number": table1["table_number"],
                    "deal_id": deal_id,
                    "contract": "3NT",
                    "declarer": "N",
                    "opening_lead": "AS",
                    "tricks_taken": 9,
                }],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        # Increase to 6 rounds
        r2 = self.client.put(
            f"/api/tournaments/{tour_id}",
            data=json.dumps({
                "name": "Test Cup",
                "date": "2025-06-01",
                "teams": [
                    {"name": "A", "member1": "A1", "member2": "A2"},
                    {"name": "B", "member1": "B1", "member2": "B2"},
                    {"name": "C", "member1": "C1", "member2": "C2"},
                    {"name": "D", "member1": "D1", "member2": "D2"},
                ],
                "num_rounds": 6,
                "deals_per_round": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        stored = self._load_tournament_file(tour_id)
        self.assertEqual(len(stored["rounds"]), 6)
        self.assertEqual(len(stored["cycles"]), 2)
        # Round 1 still has the saved result
        self.assertIn("results_by_table_deal", stored["rounds"][0])
        self.assertTrue(len(stored["rounds"][0]["results_by_table_deal"]) > 0)

    def test_update_in_progress_decrease_num_rounds_rejected_when_removed_has_results(
        self,
    ) -> None:
        data = self._create_tournament(num_rounds=6, deals_per_round=2)
        tour_id = data["id"]
        stored = self._load_tournament_file(tour_id)
        round4 = stored["rounds"][3]
        table1 = round4["tables"][0]
        deal_id = round4["deals"][0]["id"]
        r = self.client.post(
            f"/api/tournaments/{tour_id}/round-results",
            data=json.dumps({
                "round_id": 4,
                "results": [{
                    "table_number": table1["table_number"],
                    "deal_id": deal_id,
                    "contract": "3NT",
                    "declarer": "N",
                    "opening_lead": "AS",
                    "tricks_taken": 9,
                }],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        # Try to reduce to 3 rounds (would remove rounds 4,5,6; round 4 has results)
        r2 = self.client.put(
            f"/api/tournaments/{tour_id}",
            data=json.dumps({
                "name": "Test Cup",
                "date": "2025-06-01",
                "teams": [
                    {"name": "A", "member1": "A1", "member2": "A2"},
                    {"name": "B", "member1": "B1", "member2": "B2"},
                    {"name": "C", "member1": "C1", "member2": "C2"},
                    {"name": "D", "member1": "D1", "member2": "D2"},
                ],
                "num_rounds": 3,
                "deals_per_round": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 400)
        err = r2.get_json()
        self.assertIn("errors", err)
        self.assertTrue(
            any("usunięte" in str(e) or "wyniki" in str(e) for e in err["errors"])
        )
        stored = self._load_tournament_file(tour_id)
        self.assertEqual(len(stored["rounds"]), 6)


if __name__ == "__main__":
    unittest.main()
