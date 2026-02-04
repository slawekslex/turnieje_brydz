"""
Flask API: tournament list and create endpoints.
"""

import uuid
from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, render_template

from bridge.models.round_models import Team, TeamMember, standard_16_board_deal_sequence
from bridge.models.tournament import Tournament
from bridge.services.generator import (
    generate_random_round_robin,
    validate_round_robin,
    assign_deals_to_rounds,
)
from bridge.storage import load_index, save_index, save_tournament, ensure_data_dir

bp = Blueprint("api", __name__, url_prefix="")

DEALS_PER_ROUND = 2


def _data_dir() -> Path:
    return Path(current_app.config["DATA_DIR"])


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/tournaments", methods=["GET"])
def list_tournaments():
    """Return list of tournaments: [{ id, name, date }, ...]."""
    entries = load_index(_data_dir())
    return jsonify(entries)


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

    schedule_rounds = generate_random_round_robin(teams)
    validate_round_robin(teams, schedule_rounds)
    deal_seq = standard_16_board_deal_sequence(start_id=1)
    rounds = assign_deals_to_rounds(schedule_rounds, DEALS_PER_ROUND, deal_seq)

    tournament = Tournament(name=name, date=tournament_date, teams=teams, rounds=rounds)
    tour_id = str(uuid.uuid4())
    path = _data_dir() / f"{tour_id}.json"
    save_tournament(tournament, path)

    entries = load_index(_data_dir())
    entries.append({"id": tour_id, "name": name, "date": date_str})
    save_index(_data_dir(), entries)

    return jsonify({"ok": True, "id": tour_id, "name": name, "date": date_str})
