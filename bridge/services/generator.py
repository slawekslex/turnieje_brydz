from typing import Dict, Iterator, List, Set, Tuple, Optional
import random

from bridge.models.round_models import Team, Deal, Round, TableAssignment, TableNumber


def generate_round_robin(
    teams: List[Team],
) -> List[Round]:
    """
    Generate a round-robin tournament schedule using the circle method.

    Assumptions:
    - Number of teams N is even and >= 2.

    Behaviour (structure only, no deals):
    - Each pair of teams meets exactly once over N-1 rounds.
    - For each round, deals_per_round new deals are drawn from deal_generator.

    Returns a list of Round objects with:
    - tables filled (NS / EW per table)
    - deals list left empty
    - results_by_table_deal initially empty
    """
    num_teams = len(teams)
    if num_teams < 2 or num_teams % 2 != 0:
        raise ValueError("Number of teams must be an even integer >= 2")

    # Copy to avoid mutating the caller's list
    rotation = teams[:]

    num_rounds = num_teams - 1
    rounds: List[Round] = []

    for round_index in range(num_rounds):
        round_number = round_index + 1

        table_assignments: List[TableAssignment] = []
        num_tables = num_teams // 2

        for table_index in range(num_tables):
            # Pair the i-th team from the start with the i-th from the end
            home = rotation[table_index]
            away = rotation[-(table_index + 1)]

            # Simple NS/EW assignment with alternation by round:
            # on odd rounds, "home" is NS; on even rounds, "home" is EW
            if round_number % 2 == 1:
                ns_team_id = home.id
                ew_team_id = away.id
            else:
                ns_team_id = away.id
                ew_team_id = home.id

            table_number: TableNumber = table_index + 1
            table_assignments.append(
                TableAssignment(
                    table_number=table_number,
                    ns_team_id=ns_team_id,
                    ew_team_id=ew_team_id,
                )
            )

        rounds.append(
            Round(
                id=round_number,
                round_number=round_number,
                tables=table_assignments,
                deals=[],
                results_by_table_deal={},
            )
        )

        # Circle method rotation:
        # Keep the first team fixed, rotate the others clockwise.
        fixed = rotation[0]
        rest = rotation[1:]
        rest = [rest[-1]] + rest[:-1]
        rotation = [fixed] + rest

    return rounds


def validate_round_robin(teams: List[Team], rounds: List[Round]) -> None:
    """
    Validate that the given rounds form a proper single round-robin:

    - Every team plays every other team exactly once.
    - No team appears more than once in the same round.
    - All team ids in the rounds come from the provided teams list.

    Raises ValueError with a descriptive message if the schedule is invalid.
    """
    if not teams:
        raise ValueError("Team list must not be empty")

    team_ids: List[int] = [t.id for t in teams]
    team_id_set: Set[int] = set(team_ids)

    if len(team_ids) != len(team_id_set):
        raise ValueError("Team ids must be unique")

    expected_rounds = len(team_ids) - 1
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


def generate_random_round_robin(
    teams: List[Team],
    rng: Optional[random.Random] = None,
) -> List[Round]:
    """
    Generate a random round-robin schedule.

    - Uses a random permutation of the teams as the initial ordering
      for the circle method.
    - For each pairing at each table, randomly assigns which team
      sits NS and which sits EW.
    - Only the structural schedule (tables per round) is built here;
      deals are not assigned.
    """
    if rng is None:
        rng = random.Random()

    num_teams = len(teams)
    if num_teams < 2 or num_teams % 2 != 0:
        raise ValueError("Number of teams must be an even integer >= 2")

    rotation = teams[:]
    rng.shuffle(rotation)

    num_rounds = num_teams - 1
    rounds: List[Round] = []

    for round_index in range(num_rounds):
        round_number = round_index + 1

        table_assignments: List[TableAssignment] = []
        num_tables = num_teams // 2

        for table_index in range(num_tables):
            home = rotation[table_index]
            away = rotation[-(table_index + 1)]

            if rng.random() < 0.5:
                ns_team_id = home.id
                ew_team_id = away.id
            else:
                ns_team_id = away.id
                ew_team_id = home.id

            table_number: TableNumber = table_index + 1
            table_assignments.append(
                TableAssignment(
                    table_number=table_number,
                    ns_team_id=ns_team_id,
                    ew_team_id=ew_team_id,
                )
            )

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

    cycle_a = generate_random_round_robin(teams, rng=rng)
    validate_round_robin(teams, cycle_a)

    best_b: Optional[List[Round]] = None
    best_score: Optional[int] = None

    for _ in range(k):
        candidate_b = generate_random_round_robin(teams, rng=rng)
        validate_round_robin(teams, candidate_b)

        score = score_cycle_difference(cycle_a, candidate_b)

        if best_score is None or score < best_score:
            best_score = score
            best_b = candidate_b

    assert best_b is not None and best_score is not None

    print(f"Best difference score over {k} candidates: {best_score}")

    return cycle_a, best_b
