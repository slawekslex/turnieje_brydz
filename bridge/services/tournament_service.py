"""
Parse and validate tournament create/update payloads; build teams and rounds.
"""

from datetime import date
from typing import Any

from bridge.models.round_models import Team, TeamMember
from bridge.services.generator import (
    DEFAULT_DEALS_PER_ROUND,
    build_rounds_from_cycles,
    cycles_from_num_rounds_and_deals,
)


def parse_tournament_payload(body: dict) -> tuple[Any, list]:
    """
    Parse and validate tournament payload (create/update).
    Returns (name, tournament_date, teams, cycles, rounds) or (None, errors).
    """
    name = (body.get("name") or "").strip()
    date_str = body.get("date") or ""
    teams_data = body.get("teams") or []
    errors = []

    if not name:
        errors.append("Nazwa jest wymagana.")
    if not date_str:
        errors.append("Data jest wymagana.")
    else:
        try:
            tournament_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append("Nieprawidłowa data; użyj formatu RRRR-MM-DD.")
            tournament_date = None
    if len(teams_data) < 2:
        errors.append("Wymagane są co najmniej 2 drużyny.")
    if len(teams_data) % 2 != 0:
        errors.append("Liczba drużyn musi być parzysta.")

    if errors:
        return None, errors

    teams = []
    for i, t in enumerate(teams_data):
        team_name = (t.get("name") or "").strip()
        m1 = (t.get("member1") or "").strip()
        m2 = (t.get("member2") or "").strip()
        if not team_name:
            errors.append(f"Drużyna {i + 1}: nazwa jest wymagana.")
        if not m1:
            errors.append(f"Drużyna {i + 1}: członek 1 jest wymagany.")
        if not m2:
            errors.append(f"Drużyna {i + 1}: członek 2 jest wymagany.")
        if team_name and m1 and m2:
            teams.append(
                Team(
                    id=i + 1,
                    name=team_name,
                    member1=TeamMember(m1),
                    member2=TeamMember(m2),
                )
            )
    if errors:
        return None, errors

    # Duplicate team names
    names = [t.name for t in teams]
    seen: set[str] = set()
    duplicates: list[str] = []
    for n in names:
        if n in seen and n not in duplicates:
            duplicates.append(n)
        seen.add(n)
    if duplicates:
        errors.append(
            "Dwie lub więcej drużyn mają tę samą nazwę: " + ", ".join(duplicates) + "."
        )
        return None, errors

    num_rounds_raw = body.get("num_rounds")
    deals_per_round = max(0, int(body.get("deals_per_round") or DEFAULT_DEALS_PER_ROUND))
    if num_rounds_raw is not None:
        num_rounds = max(0, int(num_rounds_raw))
        cycles = cycles_from_num_rounds_and_deals(len(teams), num_rounds, deals_per_round)
        rounds = build_rounds_from_cycles(teams, cycles) if cycles else []
    else:
        cycles = body.get("cycles") or [{"deals_per_round": DEFAULT_DEALS_PER_ROUND}]
        rounds = build_rounds_from_cycles(teams, cycles)

    return (name, tournament_date, teams, cycles, rounds), []
