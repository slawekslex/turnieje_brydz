"""Demo: generate three round-robin cycles for 6 teams, print pairings and penalty scores."""
import random

from bridge.models.round_models import Team, TeamMember
from bridge.services.generator import add_round_robin, score_cycle_difference


def print_cycle_pairings(cycle_label: str, rounds: list) -> None:
    """Print pairings for one cycle: round number, table, NS team, EW team."""
    print(f"\n--- {cycle_label} ---")
    for rnd in rounds:
        print(f"  Round {rnd.round_number}:")
        for table in rnd.tables:
            print(
                f"    Table {table.table_number}: "
                f"Team {table.ns_team_id} (NS) vs Team {table.ew_team_id} (EW)"
            )


def main() -> None:
    teams = [
        Team(
            id=i,
            name=f"Team {i}",
            member1=TeamMember(f"Player {i}A"),
            member2=TeamMember(f"Player {i}B"),
        )
        for i in range(1, 7)
    ]

    rng = random.Random(42)

    cycle_a = add_round_robin(teams, [], k=100, rng=rng)
    cycle_b = add_round_robin(teams, [cycle_a], k=50, rng=rng)
    cycle_c = add_round_robin(teams, [cycle_a, cycle_b], k=50, rng=rng)

    print("Three cycles for 6 teams (pairings)")
    print_cycle_pairings("Cycle A", cycle_a)
    print_cycle_pairings("Cycle B", cycle_b)
    print_cycle_pairings("Cycle C", cycle_c)

    score_ab = score_cycle_difference(cycle_a, cycle_b)
    score_ac = score_cycle_difference(cycle_a, cycle_c)
    score_bc = score_cycle_difference(cycle_b, cycle_c)

    print("\n--- Penalty scores (lower = more distinct) ---")
    print(f"  A vs B: {score_ab}")
    print(f"  A vs C: {score_ac}")
    print(f"  B vs C: {score_bc}")
    print(f"  Total: {score_ab + score_ac + score_bc}")


if __name__ == "__main__":
    main()
