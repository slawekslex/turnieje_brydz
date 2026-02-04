"""
Flask API: tournament list and create endpoints.
"""

import uuid
from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, render_template

from bridge.models.round_models import (
    Round,
    Team,
    TeamMember,
    standard_16_board_deal_sequence,
)
from bridge.models.tournament import Tournament
from bridge.services.generator import (
    generate_random_round_robin,
    validate_round_robin,
    assign_deals_to_rounds,
)
from bridge.storage import (
    load_index,
    load_tournament,
    load_tournament_cycles,
    save_index,
    save_tournament,
    ensure_data_dir,
)

bp = Blueprint("api", __name__, url_prefix="")

DEALS_PER_ROUND = 2


def _data_dir() -> Path:
    return Path(current_app.config["DATA_DIR"])


def _tournament_path(tour_id: str) -> Path:
    return _data_dir() / f"{tour_id}.json"


def _build_rounds_from_cycles(teams, cycles: list) -> list:
    """Build full rounds list from cycles: each cycle is one round-robin with deals_per_round."""
    if not cycles:
        cycles = [{"deals_per_round": DEALS_PER_ROUND}]
    rounds_per_cycle = len(teams) - 1
    all_rounds = []
    deal_id_start = 1
    global_round_id = 1
    for c in cycles:
        deals_per_round = max(0, int(c.get("deals_per_round") or 0))
        schedule = generate_random_round_robin(teams)
        validate_round_robin(teams, schedule)
        deal_seq = standard_16_board_deal_sequence(start_id=deal_id_start)
        cycle_rounds = assign_deals_to_rounds(schedule, deals_per_round, deal_seq)
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
        deal_id_start += rounds_per_cycle * deals_per_round
    return all_rounds


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/tournament/<tour_id>")
def tournament_edit_page(tour_id: str):
    """Serve the tournament edit page."""
    path = _tournament_path(tour_id)
    if not path.exists():
        return render_template("404.html"), 404
    return render_template("tournament_edit.html", tour_id=tour_id)


@bp.route("/api/tournaments", methods=["GET"])
def list_tournaments():
    """Return list of non-archived tournaments: [{ id, name, date }, ...]."""
    entries = load_index(_data_dir())
    active = [e for e in entries if not e.get("archived")]
    return jsonify(active)


@bp.route("/api/tournaments/<tour_id>", methods=["GET"])
def get_tournament(tour_id: str):
    """Return a single tournament for editing: { id, name, date, teams }."""
    path = _tournament_path(tour_id)
    if not path.exists():
        return jsonify({"error": "Not found"}), 404
    tournament = load_tournament(path)
    teams_data = [
        {
            "name": t.name,
            "member1": t.member1.name,
            "member2": t.member2.name,
        }
        for t in tournament.teams
    ]
    cycles = load_tournament_cycles(path)
    return jsonify({
        "id": tour_id,
        "name": tournament.name,
        "date": tournament.date.isoformat(),
        "teams": teams_data,
        "cycles": cycles,
    })


@bp.route("/api/tournaments", methods=["POST"])
def create_tournament():
    """
    Create a new tournament.
    Body: { "name": str, "date": "YYYY-MM-DD", "teams": [ { "name": str, "member1": str, "member2": str }, ... ] }
    Teams must be even, >= 2.
    """
    ensure_data_dir(_data_dir())
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    date_str = body.get("date") or ""
    teams_data = body.get("teams") or []

    errors = []
    if not name:
        errors.append("Name is required.")
    if not date_str:
        errors.append("Date is required.")
    else:
        try:
            tournament_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append("Invalid date; use YYYY-MM-DD.")
            tournament_date = None
    if len(teams_data) < 2:
        errors.append("At least 2 teams are required.")
    if len(teams_data) % 2 != 0:
        errors.append("Number of teams must be even.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    teams = []
    for i, t in enumerate(teams_data):
        team_name = (t.get("name") or "").strip()
        m1 = (t.get("member1") or "").strip()
        m2 = (t.get("member2") or "").strip()
        if not team_name:
            errors.append(f"Team {i + 1}: name is required.")
        if not m1:
            errors.append(f"Team {i + 1}: member 1 name is required.")
        if not m2:
            errors.append(f"Team {i + 1}: member 2 name is required.")
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
        return jsonify({"ok": False, "errors": errors}), 400

    cycles = body.get("cycles") or [{"deals_per_round": DEALS_PER_ROUND}]
    rounds = _build_rounds_from_cycles(teams, cycles)

    tournament = Tournament(name=name, date=tournament_date, teams=teams, rounds=rounds)
    tour_id = str(uuid.uuid4())
    path = _data_dir() / f"{tour_id}.json"
    save_tournament(tournament, path, cycles=cycles)

    entries = load_index(_data_dir())
    entries.append({"id": tour_id, "name": name, "date": date_str, "archived": False})
    save_index(_data_dir(), entries)

    return jsonify({"ok": True, "id": tour_id, "name": name, "date": date_str})


@bp.route("/api/tournaments/<tour_id>/archive", methods=["POST"])
def archive_tournament(tour_id: str):
    """Mark a tournament as archived (excluded from main list)."""
    path = _tournament_path(tour_id)
    if not path.exists():
        return jsonify({"ok": False, "error": "Not found"}), 404
    entries = load_index(_data_dir())
    for i, e in enumerate(entries):
        if e.get("id") == tour_id:
            entries[i] = {**e, "archived": True}
            save_index(_data_dir(), entries)
            return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Not found"}), 404


@bp.route("/api/tournaments/<tour_id>", methods=["PUT"])
def update_tournament(tour_id: str):
    """
    Update an existing tournament.
    Body: same as POST create (name, date, teams). Regenerates schedule.
    """
    path = _tournament_path(tour_id)
    if not path.exists():
        return jsonify({"ok": False, "errors": ["Turniej nie istnieje."]}), 404

    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    date_str = body.get("date") or ""
    teams_data = body.get("teams") or []

    errors = []
    if not name:
        errors.append("Name is required.")
    if not date_str:
        errors.append("Date is required.")
    else:
        try:
            tournament_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append("Invalid date; use YYYY-MM-DD.")
            tournament_date = None
    if len(teams_data) < 2:
        errors.append("At least 2 teams are required.")
    if len(teams_data) % 2 != 0:
        errors.append("Number of teams must be even.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    teams = []
    for i, t in enumerate(teams_data):
        team_name = (t.get("name") or "").strip()
        m1 = (t.get("member1") or "").strip()
        m2 = (t.get("member2") or "").strip()
        if not team_name:
            errors.append(f"Team {i + 1}: name is required.")
        if not m1:
            errors.append(f"Team {i + 1}: member 1 name is required.")
        if not m2:
            errors.append(f"Team {i + 1}: member 2 name is required.")
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
        return jsonify({"ok": False, "errors": errors}), 400

    cycles = body.get("cycles") or [{"deals_per_round": DEALS_PER_ROUND}]
    rounds = _build_rounds_from_cycles(teams, cycles)

    tournament = Tournament(name=name, date=tournament_date, teams=teams, rounds=rounds)
    save_tournament(tournament, path, cycles=cycles)

    entries = load_index(_data_dir())
    for i, e in enumerate(entries):
        if e.get("id") == tour_id:
            entries[i] = {"id": tour_id, "name": name, "date": date_str, "archived": e.get("archived", False)}
            break
    save_index(_data_dir(), entries)

    return jsonify({"ok": True, "id": tour_id, "name": name, "date": date_str})
