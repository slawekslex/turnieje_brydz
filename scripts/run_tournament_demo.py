"""Demo: generate random round-robin and assign deals."""
from itertools import count

from bridge.models.round_models import Team, TeamMember, deal_from_board_number
from bridge.services.generator import (
    generate_random_round_robin,
    validate_round_robin,
    assign_deals_to_rounds,
)


def deal_sequence():
    """Infinite sequence of Deal objects with consecutive ids starting from 1."""
    for board_id in count(1):
        yield deal_from_board_number(board_id)


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
    deals_per_round = 2

    print("Random round-robin:")
    schedule_rounds = generate_random_round_robin(teams)
    validate_round_robin(teams, schedule_rounds)

    random_rounds = assign_deals_to_rounds(
        schedule_rounds, deals_per_round, deal_sequence()
    )

    for rnd in random_rounds:
        print(f"Round {rnd.round_number}")
        for table in rnd.tables:
            ns_team = next(t for t in teams if t.id == table.ns_team_id)
            ew_team = next(t for t in teams if t.id == table.ew_team_id)
            print(
                f"  Table {table.table_number}: "
                f"NS={ns_team.name} (id={ns_team.id}), "
                f"EW={ew_team.name} (id={ew_team.id})"
            )
        print()


if __name__ == "__main__":
    main()
