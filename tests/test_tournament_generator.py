import random
import unittest
from itertools import count
from typing import Iterator, List

from bridge.models.round_models import (
    Team,
    TeamMember,
    Deal,
    Round,
    TableAssignment,
    deal_from_board_number,
)
from bridge.services.generator import (
    add_round_robin,
    generate_round_robin,
    generate_random_round_robin,
    validate_round_robin,
    assign_deals_to_rounds,
    score_cycle_difference,
    generate_two_round_robin,
)


def _make_teams(n: int) -> List[Team]:
    return [
        Team(
            id=i,
            name=f"Team {i}",
            member1=TeamMember(f"Player {i}A"),
            member2=TeamMember(f"Player {i}B"),
        )
        for i in range(1, n + 1)
    ]


def _deal_sequence() -> Iterator[Deal]:
    """Infinite deal generator with monotonically increasing ids."""
    for board_id in count(1):
        yield deal_from_board_number(board_id)


class TournamentGeneratorTests(unittest.TestCase):
    def test_generate_round_robin_structure_and_validation(self) -> None:
        teams = _make_teams(6)

        rounds = generate_round_robin(teams)

        self.assertEqual(len(rounds), 5)
        for rnd in rounds:
            self.assertEqual(len(rnd.tables), 3)

            seen_ids = []
            for table in rnd.tables:
                seen_ids.append(table.ns_team_id)
                seen_ids.append(table.ew_team_id)
            self.assertCountEqual(seen_ids, [t.id for t in teams])

            self.assertEqual(rnd.deals, [])

        validate_round_robin(teams, rounds)

    def test_generate_round_robin_invalid_team_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_round_robin(_make_teams(1))

    def test_generate_round_robin_odd_teams_with_bye(self) -> None:
        """Three teams: 3 rounds, one bye per round, 1 table per round."""
        teams = _make_teams(3)
        rounds = generate_round_robin(teams)
        self.assertEqual(len(rounds), 3)
        for rnd in rounds:
            self.assertEqual(len(rnd.tables), 1)
        validate_round_robin(teams, rounds)

    def test_generate_random_round_robin_is_valid_and_randomized(self) -> None:
        teams = _make_teams(6)
        rng = random.Random(12345)

        rounds = generate_random_round_robin(teams, rng=rng)

        self.assertEqual(len(rounds), 5)
        for rnd in rounds:
            self.assertEqual(len(rnd.tables), 3)
            self.assertEqual(len(rnd.deals), 0)

        validate_round_robin(teams, rounds)

    def test_assign_deals_to_rounds_populates_deals_correctly(self) -> None:
        teams = _make_teams(4)
        schedule_rounds = generate_round_robin(teams)
        deals_per_round = 3

        enriched = assign_deals_to_rounds(
            schedule_rounds, deals_per_round, _deal_sequence()
        )

        for rnd in schedule_rounds:
            self.assertEqual(len(rnd.deals), 0)

        all_ids = []
        for rnd in enriched:
            self.assertEqual(len(rnd.deals), deals_per_round)
            round_ids = [d.id for d in rnd.deals]
            self.assertEqual(len(set(round_ids)), deals_per_round)
            all_ids.extend(round_ids)

        self.assertEqual(sorted(all_ids), list(range(1, len(all_ids) + 1)))

    def test_assign_deals_to_rounds_negative_deals_raises(self) -> None:
        teams = _make_teams(4)
        schedule_rounds = generate_round_robin(teams)

        with self.assertRaises(ValueError):
            assign_deals_to_rounds(schedule_rounds, -1, _deal_sequence())

    def test_validate_round_robin_rejects_duplicate_team_in_round(self) -> None:
        teams = _make_teams(4)

        rounds = generate_round_robin(teams)
        bad_rounds = list(rounds)

        first_round = bad_rounds[0]
        t0 = first_round.tables[0]
        bad_tables = list(first_round.tables)
        bad_tables[1] = TableAssignment(
            table_number=bad_tables[1].table_number,
            ns_team_id=t0.ns_team_id,
            ew_team_id=bad_tables[1].ew_team_id,
        )
        bad_rounds[0] = Round(
            id=first_round.id,
            round_number=first_round.round_number,
            tables=bad_tables,
            deals=first_round.deals,
            results_by_table_deal=first_round.results_by_table_deal,
        )

        with self.assertRaises(ValueError):
            validate_round_robin(teams, bad_rounds)

    def test_score_cycle_difference_small_case(self) -> None:
        team1 = Team(
            id=1,
            name="T1",
            member1=TeamMember("Alice"),
            member2=TeamMember("Bob"),
        )
        team2 = Team(
            id=2,
            name="T2",
            member1=TeamMember("Carol"),
            member2=TeamMember("Dave"),
        )

        round_a = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(table_number=1, ns_team_id=1, ew_team_id=2),
            ],
            deals=[],
            results_by_table_deal={},
        )

        round_b_same = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(table_number=1, ns_team_id=1, ew_team_id=2),
            ],
            deals=[],
            results_by_table_deal={},
        )
        score_same = score_cycle_difference([round_a], [round_b_same])
        self.assertEqual(score_same, 5 + 1)

        round_b_flipped = Round(
            id=1,
            round_number=1,
            tables=[
                TableAssignment(table_number=1, ns_team_id=2, ew_team_id=1),
            ],
            deals=[],
            results_by_table_deal={},
        )
        score_flipped = score_cycle_difference([round_a], [round_b_flipped])
        self.assertEqual(score_flipped, 5)

    def test_generate_two_round_robin_returns_valid_cycles(self) -> None:
        teams = _make_teams(6)
        rng = random.Random(42)

        A, B = generate_two_round_robin(teams, k=10, rng=rng)

        validate_round_robin(teams, A)
        validate_round_robin(teams, B)

        self.assertEqual(len(A), 5)
        self.assertEqual(len(B), 5)

        score = score_cycle_difference(A, B)
        self.assertGreaterEqual(score, 0)

    def test_add_round_robin_generates_three_cycles(self) -> None:
        teams = _make_teams(6)
        rng = random.Random(999)

        cycle_a = add_round_robin(teams, [], k=100, rng=rng)
        cycle_b = add_round_robin(teams, [cycle_a], k=50, rng=rng)
        cycle_c = add_round_robin(teams, [cycle_a, cycle_b], k=50, rng=rng)

        for cycle in (cycle_a, cycle_b, cycle_c):
            validate_round_robin(teams, cycle)
            self.assertEqual(len(cycle), 5)
            for rnd in cycle:
                self.assertEqual(len(rnd.tables), 3)

        score_ab = score_cycle_difference(cycle_a, cycle_b)
        score_ac = score_cycle_difference(cycle_a, cycle_c)
        score_bc = score_cycle_difference(cycle_b, cycle_c)
        self.assertGreaterEqual(score_ab, 0)
        self.assertGreaterEqual(score_ac, 0)
        self.assertGreaterEqual(score_bc, 0)

    def test_deterministic_pairings_without_rng(self) -> None:
        """Without passing rng, same number of teams must yield identical pairings."""
        teams6 = _make_teams(6)

        # Single cycle: two calls with no rng must match
        rounds_a = generate_random_round_robin(teams6)
        rounds_b = generate_random_round_robin(teams6)
        self._assert_same_pairings(rounds_a, rounds_b)

        # Multiple cycles via add_round_robin (no rng): repeat and compare
        cycle1_a = add_round_robin(teams6, [], k=1)
        cycle1_b = add_round_robin(teams6, [], k=1)
        self._assert_same_pairings(cycle1_a, cycle1_b)

        cycle2_a = add_round_robin(teams6, [cycle1_a], k=20)
        cycle2_b = add_round_robin(teams6, [cycle1_b], k=20)
        self._assert_same_pairings(cycle2_a, cycle2_b)

        # Different team count can differ (just sanity check we get valid schedules)
        teams4 = _make_teams(4)
        rounds4 = generate_random_round_robin(teams4)
        validate_round_robin(teams4, rounds4)
        self.assertEqual(len(rounds4), 3)

    def _assert_same_pairings(
        self, rounds_a: List[Round], rounds_b: List[Round]
    ) -> None:
        self.assertEqual(len(rounds_a), len(rounds_b))
        for rnd_a, rnd_b in zip(rounds_a, rounds_b):
            self.assertEqual(len(rnd_a.tables), len(rnd_b.tables))
            for t_a, t_b in zip(rnd_a.tables, rnd_b.tables):
                self.assertEqual(t_a.ns_team_id, t_b.ns_team_id)
                self.assertEqual(t_a.ew_team_id, t_b.ew_team_id)


if __name__ == "__main__":
    unittest.main()
