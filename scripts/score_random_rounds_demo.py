"""Demo: score similarity between two random round-robin cycles."""
import random

from bridge.models.round_models import Team, TeamMember
from bridge.services.generator import (
    generate_random_round_robin,
    score_cycle_difference,
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

    rng = random.Random()

    cycle1 = generate_random_round_robin(teams, rng=rng)
    cycle2 = generate_random_round_robin(teams, rng=rng)

    score = score_cycle_difference(cycle1, cycle2)

    print("Scoring full cycles (structure only, no deals):")
    print(f"  Rounds per cycle: {len(cycle1)}")
    print(f"  Score (lower = more distinct): {score}")


if __name__ == "__main__":
    main()
