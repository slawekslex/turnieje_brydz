"""
Parse and validate tournament create/update payloads; build teams and rounds.
Helpers for update: detect breaking changes and merge existing results.
"""

from datetime import date
from typing import Any, List, Tuple

from bridge.models.round_models import Round, Team, TeamMember
from bridge.models.tournament import Tournament
from bridge.services.generator import (
    DEFAULT_DEALS_PER_ROUND,
    build_extra_rounds,
    build_rounds_from_cycles,
    cycles_from_num_rounds_and_deals,
)


def _round_has_results(rnd: Round) -> bool:
    return bool(rnd.results_by_table_deal)


def is_update_breaking(
    existing: Tournament,
    new_teams_count: int,
    new_cycles: List[dict],
    new_num_rounds: int,
) -> Tuple[bool, List[str]]:
    """
    Determine if an update would break existing results (require clearing).
    Returns (is_breaking, list of reason messages in Polish).
    """
    reasons: List[str] = []
    old_count = len(existing.teams)
    if new_teams_count != old_count:
        if new_teams_count > old_count:
            reasons.append("Dodawanie drużyny wymaga wyczyszczenia wyników.")
        else:
            reasons.append("Usuwanie drużyny wymaga wyczyszczenia wyników.")
    # deals_per_round: compare first round's deal count to new cycles
    old_dpr = len(existing.rounds[0].deals) if existing.rounds else 0
    new_dpr = (
        max(0, int(new_cycles[0].get("deals_per_round") or 0))
        if new_cycles
        else 0
    )
    if old_dpr != new_dpr:
        reasons.append("Zmiana liczby rozdań na rundę wymaga wyczyszczenia wyników.")
    old_num_rounds = len(existing.rounds)
    if new_num_rounds < old_num_rounds:
        # Check if any dropped round has results
        dropped_has_results = any(
            _round_has_results(rnd)
            for rnd in existing.rounds[new_num_rounds:]
        )
        if dropped_has_results:
            reasons.append(
                "Zmniejszenie liczby rund poniżej rund z wpisanymi wynikami "
                "wymaga wyczyszczenia wyników."
            )
    return (len(reasons) > 0, reasons)


def apply_non_breaking_update(
    existing: Tournament,
    name: str,
    tournament_date: date,
    teams: List[Team],
    new_num_rounds: int,
    new_cycles: List[dict],
    number_of_boxes: int | None = None,
) -> Tournament:
    """
    Apply a non-breaking update: keep existing rounds (and their results), update
    name, date, teams. Trim rounds if new_num_rounds is smaller (dropped rounds
    must have no results; caller ensures this). Append rounds if new_num_rounds
    is larger.
    """
    rounds = list(existing.rounds)
    new_dpr = (
        max(0, int(new_cycles[0].get("deals_per_round") or 0))
        if new_cycles
        else DEFAULT_DEALS_PER_ROUND
    )
    if new_num_rounds < len(rounds):
        rounds = rounds[:new_num_rounds]
    elif new_num_rounds > len(rounds):
        boxes = number_of_boxes if number_of_boxes is not None else existing.number_of_boxes
        extra = build_extra_rounds(
            teams,
            rounds,
            new_num_rounds - len(rounds),
            new_dpr,
            number_of_boxes=boxes,
        )
        rounds = rounds + extra
    boxes = number_of_boxes if number_of_boxes is not None else existing.number_of_boxes
    return Tournament(
        name=name,
        date=tournament_date,
        teams=teams,
        rounds=rounds,
        number_of_boxes=boxes,
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
    number_of_boxes = max(1, int(body.get("number_of_boxes") or 1))
    if num_rounds_raw is not None:
        num_rounds = max(0, int(num_rounds_raw))
        cycles = cycles_from_num_rounds_and_deals(len(teams), num_rounds, deals_per_round)
        rounds = (
            build_rounds_from_cycles(teams, cycles, number_of_boxes=number_of_boxes)
            if cycles
            else []
        )
    else:
        cycles = body.get("cycles") or [{"deals_per_round": DEFAULT_DEALS_PER_ROUND}]
        rounds = build_rounds_from_cycles(
            teams, cycles, number_of_boxes=number_of_boxes
        )

    return (name, tournament_date, teams, cycles, rounds), []
