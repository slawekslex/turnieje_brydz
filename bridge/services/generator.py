from typing import Dict, Iterator, List, Set, Tuple, Optional
import random

from bridge.models.round_models import (
    Deal,
    Round,
    TableAssignment,
    Team,
    TableNumber,
    standard_16_board_deal_sequence,
)


def _rounds_per_cycle(num_teams: int) -> int:
    """Rounds in one full round-robin: even n -> n-1, odd n (with bye) -> n."""
    if num_teams < 2:
        return 0
    return num_teams if num_teams % 2 == 1 else num_teams - 1


def generate_round_robin(
    teams: List[Team],
) -> List[Round]:
    """
    Generate a round-robin tournament schedule using the circle method.

    Assumptions:
    - Number of teams N >= 2. Even N: N-1 rounds, each round N/2 tables.
    - Odd N: N rounds, one team has bye each round, (N-1)/2 tables per round.

    Returns a list of Round objects with tables filled, deals empty.
    """
    num_teams = len(teams)
    if num_teams < 2:
        raise ValueError("Number of teams must be >= 2")

    if num_teams % 2 == 0:
        rotation: List[Optional[Team]] = teams[:]
        num_rounds = num_teams - 1
    else:
        # Odd: add virtual bye slot; circle method with n+1 positions
        rotation = teams[:] + [None]
        num_rounds = num_teams

    rounds: List[Round] = []
    n = len(rotation)

    for round_index in range(num_rounds):
        round_number = round_index + 1
        table_assignments: List[TableAssignment] = []
        table_number = 1

        for i in range((n + 1) // 2):
            home = rotation[i]
            away = rotation[n - 1 - i]
            if home is None or away is None:
                continue
            if round_number % 2 == 1:
                ns_team_id = home.id
                ew_team_id = away.id
            else:
                ns_team_id = away.id
                ew_team_id = home.id
            table_assignments.append(
                TableAssignment(
                    table_number=table_number,
                    ns_team_id=ns_team_id,
                    ew_team_id=ew_team_id,
                )
            )
            table_number += 1

        rounds.append(
            Round(
                id=round_number,
                round_number=round_number,
                tables=table_assignments,
                deals=[],
                results_by_table_deal={},
            )
        )

        fixed = rotation[0]
        rest = rotation[1:]
        rest = [rest[-1]] + rest[:-1]
        rotation = [fixed] + rest

    return rounds


def validate_round_robin(teams: List[Team], rounds: List[Round]) -> None:
    """
    Validate that the given rounds form a proper single round-robin:

    - Every team plays every other team exactly once.
    - No team appears more than once in the same round (or has bye).
    - For odd N, each round has (N-1)/2 tables and one team has bye.

    Raises ValueError with a descriptive message if the schedule is invalid.
    """
    if not teams:
        raise ValueError("Team list must not be empty")

    team_ids: List[int] = [t.id for t in teams]
    team_id_set: Set[int] = set(team_ids)
    num_teams = len(team_ids)

    if len(team_ids) != len(team_id_set):
        raise ValueError("Team ids must be unique")

    expected_rounds = _rounds_per_cycle(num_teams)
    if len(rounds) != expected_rounds:
        raise ValueError(
            f"Invalid number of rounds: expected {expected_rounds}, got {len(rounds)}"
        )

    pair_counts: Dict[Tuple[int, int], int] = {}

    for rnd in rounds:
        seen_in_round: Set[int] = set()

        for table in rnd.tables:
            ns_id = table.ns_team_id
            ew_id = table.ew_team_id

            if ns_id not in team_id_set or ew_id not in team_id_set:
                raise ValueError(
                    f"Unknown team id in round {rnd.round_number}, table "
                    f"{table.table_number}: NS={ns_id}, EW={ew_id}"
                )

            for tid in (ns_id, ew_id):
                if tid in seen_in_round:
                    raise ValueError(
                        f"Team {tid} appears more than once in round "
                        f"{rnd.round_number}"
                    )
                seen_in_round.add(tid)

            pair = (ns_id, ew_id) if ns_id < ew_id else (ew_id, ns_id)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    # For odd N, each round one team has bye so (num_teams - 1) teams play per round
    expected_tables_per_round = (num_teams - 1) // 2 if num_teams % 2 == 1 else num_teams // 2
    for rnd in rounds:
        if len(rnd.tables) != expected_tables_per_round:
            raise ValueError(
                f"Round {rnd.round_number}: expected {expected_tables_per_round} tables, got {len(rnd.tables)}"
            )

    required_pairs: Set[Tuple[int, int]] = set()
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            a = team_ids[i]
            b = team_ids[j]
            pair = (a, b) if a < b else (b, a)
            required_pairs.add(pair)

    for pair in required_pairs:
        count = pair_counts.get(pair, 0)
        if count == 0:
            raise ValueError(f"Pair {pair} never plays")
        if count > 1:
            raise ValueError(f"Pair {pair} plays {count} times (expected 1)")

    for pair in pair_counts.keys():
        if pair not in required_pairs:
            raise ValueError(f"Unexpected pair found in schedule: {pair}")

    print("Round-robin schedule is valid")


def _generate_single_random_round_robin(
    teams: List[Team],
    rng: random.Random,
) -> List[Round]:
    """
    Generate one random round-robin cycle (circle method + random NS/EW).
    Supports even and odd number of teams (odd: one bye per round).
    """
    num_teams = len(teams)
    if num_teams < 2:
        raise ValueError("Number of teams must be >= 2")

    rotation_list = teams[:]
    rng.shuffle(rotation_list)
    if num_teams % 2 == 0:
        rotation = rotation_list
        num_rounds = num_teams - 1
        n = num_teams
    else:
        rotation = rotation_list + [None]
        num_rounds = num_teams
        n = num_teams + 1

    rounds: List[Round] = []

    for round_index in range(num_rounds):
        round_number = round_index + 1
        table_assignments: List[TableAssignment] = []
        table_number = 1

        for i in range((n + 1) // 2):
            home = rotation[i]
            away = rotation[n - 1 - i]
            if home is None or away is None:
                continue
            if rng.random() < 0.5:
                ns_team_id = home.id
                ew_team_id = away.id
            else:
                ns_team_id = away.id
                ew_team_id = home.id
            table_assignments.append(
                TableAssignment(
                    table_number=table_number,
                    ns_team_id=ns_team_id,
                    ew_team_id=ew_team_id,
                )
            )
            table_number += 1

        rounds.append(
            Round(
                id=round_number,
                round_number=round_number,
                tables=table_assignments,
                deals=[],
                results_by_table_deal={},
            )
        )

        fixed = rotation[0]
        rest = rotation[1:]
        rest = [rest[-1]] + rest[:-1]
        rotation = [fixed] + rest

    return rounds


def add_round_robin(
    teams: List[Team],
    existing_cycles: List[List[Round]],
    k: int = 100,
    rng: Optional[random.Random] = None,
) -> List[Round]:
    """
    Add a new round-robin cycle that minimizes penalty across all existing cycles.

    Tries k random round-robin schedules and returns the one with the lowest
    total penalty (sum of score_cycle_difference with each existing cycle).
    When existing_cycles is empty, samples once and returns that cycle.
    """
    if rng is None:
        rng = random.Random()

    if k <= 0:
        raise ValueError("k must be a positive integer")

    num_teams = len(teams)
    if num_teams < 2:
        raise ValueError("Number of teams must be >= 2")

    if not existing_cycles:
        cycle = _generate_single_random_round_robin(teams, rng)
        validate_round_robin(teams, cycle)
        return cycle

    best_cycle: Optional[List[Round]] = None
    best_total_penalty: Optional[int] = None

    for _ in range(k):
        candidate = _generate_single_random_round_robin(teams, rng)
        validate_round_robin(teams, candidate)

        total_penalty = 0
        for existing in existing_cycles:
            total_penalty += score_cycle_difference(candidate, existing)

        if best_total_penalty is None or total_penalty < best_total_penalty:
            best_total_penalty = total_penalty
            best_cycle = candidate

    assert best_cycle is not None and best_total_penalty is not None
    return best_cycle


def generate_random_round_robin(
    teams: List[Team],
    rng: Optional[random.Random] = None,
) -> List[Round]:
    """
    Generate a random round-robin schedule (single cycle, no penalty minimization).

    Convenience wrapper around add_round_robin(teams, [], k=1).
    """
    return add_round_robin(teams, [], k=1, rng=rng)


def score_cycle_difference(
    cycle1: List[Round],
    cycle2: List[Round],
    pairings_penalty: int = 5,
    ns_line_penalty: int = 1,
) -> int:
    """
    Score how similar two round-robin cycles are.

    Lower score means more distinct.
    """
    score = 0

    def round_pairings(rnd: Round) -> Set[Tuple[int, int]]:
        pairs: Set[Tuple[int, int]] = set()
        for table in rnd.tables:
            a = table.ns_team_id
            b = table.ew_team_id
            if a == b:
                continue
            pair = (a, b) if a < b else (b, a)
            pairs.add(pair)
        return pairs

    def round_ns_set(rnd: Round) -> Set[int]:
        return {table.ns_team_id for table in rnd.tables}

    pairings1 = [round_pairings(r) for r in cycle1]
    ns_sets1 = [round_ns_set(r) for r in cycle1]

    pairings2 = [round_pairings(r) for r in cycle2]
    ns_sets2 = [round_ns_set(r) for r in cycle2]

    for i in range(len(cycle1)):
        for j in range(len(cycle2)):
            if pairings1[i] == pairings2[j]:
                score += pairings_penalty
            if ns_sets1[i] == ns_sets2[j]:
                score += ns_line_penalty

    return score


def assign_deals_to_rounds(
    rounds: List[Round],
    deals_per_round: int,
    deal_generator: Iterator[Deal],
) -> List[Round]:
    """
    Given a structural schedule (rounds with tables filled, no deals),
    assign deals to each round.
    """
    if deals_per_round < 0:
        raise ValueError("deals_per_round must be >= 0")

    enriched_rounds: List[Round] = []

    for rnd in rounds:
        round_deals: List[Deal] = [next(deal_generator) for _ in range(deals_per_round)]

        enriched_rounds.append(
            Round(
                id=rnd.id,
                round_number=rnd.round_number,
                tables=rnd.tables,
                deals=round_deals,
                results_by_table_deal={},
            )
        )

    return enriched_rounds


def generate_two_round_robin(
    teams: List[Team],
    k: int = 100,
    rng: Optional[random.Random] = None,
) -> Tuple[List[Round], List[Round]]:
    """
    Generate two round-robin cycles A and B where B is chosen to be
    as distinct as possible from A (according to score_cycle_difference).
    """
    if rng is None:
        rng = random.Random()

    if k <= 0:
        raise ValueError("k must be a positive integer")

    cycle_a = add_round_robin(teams, [], k=1, rng=rng)
    cycle_b = add_round_robin(teams, [cycle_a], k=k, rng=rng)

    score = score_cycle_difference(cycle_a, cycle_b)
    print(f"Best difference score over {k} candidates: {score}")

    return cycle_a, cycle_b


DEFAULT_DEALS_PER_ROUND = 2


def cycles_from_num_rounds_and_deals(
    num_teams: int, num_rounds: int, deals_per_round: int
) -> List[dict]:
    """
    Build cycles list from total rounds and deals per round.
    One full round-robin: even teams = num_teams - 1 rounds, odd teams = num_teams rounds (bye each round).
    If num_rounds is not divisible, the last cycle is partial (use "rounds": k in that entry).
    Returns [] when num_rounds is 0.
    """
    rounds_per_cycle = _rounds_per_cycle(num_teams)
    if rounds_per_cycle <= 0:
        return [{"deals_per_round": max(0, deals_per_round)}] if num_rounds > 0 else []
    if num_rounds <= 0:
        return []
    num_full = num_rounds // rounds_per_cycle
    remainder = num_rounds % rounds_per_cycle
    cycles = [{"deals_per_round": max(0, deals_per_round)}] * num_full
    if remainder > 0:
        cycles.append({"deals_per_round": max(0, deals_per_round), "rounds": remainder})
    return cycles


def build_rounds_from_cycles(
    teams: List[Team],
    cycles: List[dict],
    deals_per_round_default: int = DEFAULT_DEALS_PER_ROUND,
    number_of_boxes: int = 1,
) -> List[Round]:
    """Build full rounds list from cycles using add_round_robin (each new cycle distinct from previous)."""
    if not cycles:
        cycles = [{"deals_per_round": deals_per_round_default}]
    number_of_boxes = max(1, number_of_boxes)
    rounds_per_cycle = _rounds_per_cycle(len(teams))
    all_rounds: List[Round] = []
    deal_id_start = 1
    global_round_id = 1
    existing_cycles: List[List[Round]] = []
    for c in cycles:
        deals_per_round = max(0, int(c.get("deals_per_round") or 0))
        rounds_in_cycle = c.get("rounds")
        if rounds_in_cycle is None:
            rounds_in_cycle = rounds_per_cycle
        else:
            rounds_in_cycle = min(max(0, int(rounds_in_cycle)), rounds_per_cycle)
        schedule = add_round_robin(teams, existing_cycles, k=100)
        validate_round_robin(teams, schedule)
        existing_cycles.append(schedule)
        deal_seq = standard_16_board_deal_sequence(
            start_id=deal_id_start, number_of_boxes=number_of_boxes
        )
        cycle_rounds = assign_deals_to_rounds(schedule, deals_per_round, deal_seq)
        cycle_rounds = cycle_rounds[:rounds_in_cycle]
        for rnd in cycle_rounds:
            all_rounds.append(
                Round(
                    id=global_round_id,
                    round_number=global_round_id,
                    tables=rnd.tables,
                    deals=rnd.deals,
                    results_by_table_deal=rnd.results_by_table_deal,
                )
            )
            global_round_id += 1
        deal_id_start += rounds_in_cycle * deals_per_round
    return all_rounds


def build_extra_rounds(
    teams: List[Team],
    existing_rounds: List[Round],
    num_extra_rounds: int,
    deals_per_round: int,
    number_of_boxes: int = 1,
) -> List[Round]:
    """
    Build additional rounds to append after existing_rounds (e.g. when increasing
    num_rounds without breaking). Uses add_round_robin so the new cycle is distinct.
    Round ids and deal ids continue from the existing rounds.
    """
    if num_extra_rounds <= 0:
        return []
    number_of_boxes = max(1, number_of_boxes)
    rounds_per_cycle = _rounds_per_cycle(len(teams))
    if rounds_per_cycle <= 0:
        return []
    # First cycle worth of existing rounds (for add_round_robin existing_cycles)
    first_cycle = existing_rounds[:rounds_per_cycle]
    existing_cycles = [[
        Round(id=r.id, round_number=r.round_number, tables=r.tables, deals=[], results_by_table_deal={})
        for r in first_cycle
    ]]
    schedule = add_round_robin(teams, existing_cycles, k=100)
    validate_round_robin(teams, schedule)
    start_round_id = len(existing_rounds) + 1
    start_deal_id = sum(len(r.deals) for r in existing_rounds) + 1
    deal_seq = standard_16_board_deal_sequence(
        start_id=start_deal_id, number_of_boxes=number_of_boxes
    )
    to_take = min(num_extra_rounds, len(schedule))
    cycle_rounds = assign_deals_to_rounds(schedule[:to_take], deals_per_round, deal_seq)
    out: List[Round] = []
    for i, rnd in enumerate(cycle_rounds):
        out.append(
            Round(
                id=start_round_id + i,
                round_number=start_round_id + i,
                tables=rnd.tables,
                deals=rnd.deals,
                results_by_table_deal={},
            )
        )
    return out
