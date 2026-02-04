"""
Flask API: tournament list and create endpoints.
"""

import uuid
from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, render_template

from bridge.models.contract import (
    CONTRACT_LEVELS,
    CONTRACT_MODIFIERS,
    CONTRACT_PATTERN,
    CONTRACT_SUITS,
    validate_contract_string,
)
from bridge.scoring import compute_score
from bridge.models.round_models import (
    Result,
    Round,
    Team,
    TeamMember,
    standard_16_board_deal_sequence,
)
from bridge.models.tournament import Tournament
from bridge.services.generator import (
    add_round_robin,
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
    """Build full rounds list from cycles using add_round_robin (each new cycle distinct from previous)."""
    if not cycles:
        cycles = [{"deals_per_round": DEALS_PER_ROUND}]
    rounds_per_cycle = len(teams) - 1
    all_rounds = []
    deal_id_start = 1
    global_round_id = 1
    existing_cycles: list = []  # list of List[Round] (structure only) for add_round_robin
    for c in cycles:
        deals_per_round = max(0, int(c.get("deals_per_round") or 0))
        schedule = add_round_robin(teams, existing_cycles, k=100)
        validate_round_robin(teams, schedule)
        existing_cycles.append(schedule)
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


@bp.route("/tournament/<tour_id>/schedule")
def tournament_schedule_page(tour_id: str):
    """Serve the tournament schedule view page."""
    path = _tournament_path(tour_id)
    if not path.exists():
        return render_template("404.html"), 404
    return render_template("tournament_schedule.html", tour_id=tour_id)


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


@bp.route("/api/tournaments/<tour_id>/schedule", methods=["GET"])
def get_tournament_schedule(tour_id: str):
    """Return tournament schedule: name, date, rounds with deals and tables (team names + results per deal)."""
    path = _tournament_path(tour_id)
    if not path.exists():
        return jsonify({"error": "Not found"}), 404
    tournament = load_tournament(path)
    team_by_id = {t.id: {"id": t.id, "name": t.name} for t in tournament.teams}
    rounds_data = []
    for rnd in tournament.rounds:
        deals_data = [
            {"id": d.id, "number": d.number, "dealer": d.dealer, "vulnerability": d.vulnerability}
            for d in rnd.deals
        ]
        tables_data = []
        for tbl in rnd.tables:
            ns = team_by_id.get(tbl.ns_team_id, {"id": tbl.ns_team_id, "name": "?"})
            ew = team_by_id.get(tbl.ew_team_id, {"id": tbl.ew_team_id, "name": "?"})
            results_by_deal = {}
            for d in rnd.deals:
                key = (tbl.table_number, d.id)
                res = rnd.results_by_table_deal.get(key)
                if res:
                    results_by_deal[str(d.id)] = {
                        "contract": res.contract or "",
                        "declarer": res.declarer or "",
                        "opening_lead": res.opening_lead or "",
                        "tricks_taken": res.tricks_taken,
                        "ns_score": res.ns_score,
                        "ew_score": res.ew_score,
                    }
                else:
                    results_by_deal[str(d.id)] = {"contract": "", "declarer": "", "opening_lead": "", "tricks_taken": None, "ns_score": 0, "ew_score": 0}
            tables_data.append({
                "table_number": tbl.table_number,
                "ns_team": ns,
                "ew_team": ew,
                "results": results_by_deal,
            })
        rounds_data.append({
            "round_number": rnd.round_number,
            "round_id": rnd.id,
            "deals": deals_data,
            "tables": tables_data,
        })
    return jsonify({
        "id": tour_id,
        "name": tournament.name,
        "date": tournament.date.isoformat(),
        "rounds": rounds_data,
    })


@bp.route("/api/contract-spec", methods=["GET"])
def contract_spec():
    """Return contract validation spec: levels, suits, modifiers, pattern (regex source)."""
    return jsonify({
        "levels": list(CONTRACT_LEVELS),
        "suits": list(CONTRACT_SUITS),
        "modifiers": [m for m in CONTRACT_MODIFIERS if m],
        "pattern": CONTRACT_PATTERN.pattern,
    })


VALID_DECLARERS = ("N", "S", "E", "W")


def _validate_result_fields(contract: str, declarer: str, opening_lead: str, tricks_taken) -> list:
    """Validate result field values. Returns list of { 'field': str, 'message': str } (empty if valid)."""
    errors = []
    contract = (contract or "").strip()
    if contract and not validate_contract_string(contract):
        errors.append({"field": "contract", "message": "Kontrakt: poziom 1–7, kolor C/D/H/S/NT, opcjonalnie x lub xx (np. 3NT, 4Sx)."})
    declarer = (declarer or "").strip().upper()
    if declarer and declarer not in VALID_DECLARERS:
        errors.append({"field": "declarer", "message": "Rozgrywający: N, S, E lub W."})
    if tricks_taken is not None and (not isinstance(tricks_taken, int) or tricks_taken < 0 or tricks_taken > 13):
        errors.append({"field": "tricks_taken", "message": "Wziątki: 0–13."})
    return errors


def _validate_result_complete(contract: str, declarer: str, opening_lead: str, tricks_taken) -> list:
    """Require all fields to be filled. Returns list of { 'field', 'message' } for empty fields."""
    errors = []
    if not (contract or "").strip():
        errors.append({"field": "contract", "message": "Wypełnij pole."})
    if not (declarer or "").strip().upper():
        errors.append({"field": "declarer", "message": "Wypełnij pole."})
    if not (opening_lead or "").strip():
        errors.append({"field": "opening_lead", "message": "Wypełnij pole."})
    if tricks_taken is None or (isinstance(tricks_taken, str) and tricks_taken.strip() == ""):
        errors.append({"field": "tricks_taken", "message": "Wypełnij pole."})
    return errors


@bp.route("/api/validate-result", methods=["POST"])
def validate_result():
    """
    Validate result fields without saving.
    Body: { contract, declarer, opening_lead, tricks_taken, vulnerability }.
    Returns 200 { valid: true, ns_score, ew_score } or 200 { valid: false, errors: [...] }.
    vulnerability is required for score (e.g. "None", "N-S", "E-W", "Both").
    """
    body = request.get_json(force=True, silent=True) or {}
    contract = (body.get("contract") or "").strip()
    declarer = (body.get("declarer") or "").strip().upper()
    opening_lead = (body.get("opening_lead") or "").strip()
    vulnerability = (body.get("vulnerability") or "").strip() or "None"
    tricks_raw = body.get("tricks_taken")
    tricks_taken = None
    if tricks_raw is not None and tricks_raw != "":
        try:
            tricks_taken = int(tricks_raw)
        except (TypeError, ValueError):
            tricks_taken = "invalid"
    errors = _validate_result_complete(contract, declarer, opening_lead, tricks_taken)
    if not errors:
        errors = _validate_result_fields(contract, declarer, opening_lead, tricks_taken)
    if errors:
        return jsonify({"valid": False, "errors": errors})
    pair = compute_score(contract, declarer, tricks_taken, vulnerability)
    if pair is None:
        return jsonify({"valid": True, "ns_score": 0, "ew_score": 0})
    ns_score, ew_score = pair
    return jsonify({"valid": True, "ns_score": ns_score, "ew_score": ew_score})


@bp.route("/api/tournaments/<tour_id>/round-results", methods=["POST"])
def save_round_results(tour_id: str):
    """
    Save deal results for one round (partial save: valid deals are saved, invalid are skipped).
    Body: { "round_id": int, "results": [ { "table_number", "deal_id", "contract", "declarer", "opening_lead", "tricks_taken" }, ... ] }
    Returns 200 { "ok": true, "saved": N, "total": M, "results": [ { "ok": true, "ns_score", "ew_score" } | { "ok": false, "error", "field" }, ... ] } (one per request item).
    """
    path = _tournament_path(tour_id)
    if not path.exists():
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    round_id = body.get("round_id")
    results_list = body.get("results") or []
    if round_id is None:
        return jsonify({"error": "round_id required"}), 400
    round_id = int(round_id)

    # Validate each result; build validated list and per-index outcome for response
    validated = []
    out_results = []
    for idx, item in enumerate(results_list):
        table_number = item.get("table_number")
        deal_id = item.get("deal_id")
        if table_number is None or deal_id is None:
            out_results.append({"ok": False, "error": "table_number and deal_id required", "field": "contract"})
            validated.append(None)
            continue
        table_number = int(table_number)
        deal_id = int(deal_id)
        contract = (item.get("contract") or "").strip()
        declarer = (item.get("declarer") or "").strip().upper()
        opening_lead = (item.get("opening_lead") or "").strip()
        tricks_raw = item.get("tricks_taken")
        tricks_taken = None
        if tricks_raw is not None:
            try:
                tricks_taken = int(tricks_raw)
            except (TypeError, ValueError):
                pass
        errs = _validate_result_complete(contract, declarer, opening_lead, tricks_taken)
        if not errs:
            errs = _validate_result_fields(contract, declarer, opening_lead, tricks_taken)
        if errs:
            out_results.append({"ok": False, "error": errs[0]["message"], "field": errs[0]["field"]})
            validated.append(None)
        else:
            validated.append({
                "table_number": table_number,
                "deal_id": deal_id,
                "contract": contract,
                "declarer": declarer,
                "opening_lead": opening_lead,
                "tricks_taken": tricks_taken,
            })
            out_results.append(None)  # placeholder, fill after save

    tournament = load_tournament(path)
    rnd = next((r for r in tournament.rounds if r.id == round_id), None)
    if not rnd:
        return jsonify({"error": "Round not found"}), 404

    saved_count = 0
    for idx, v in enumerate(validated):
        if v is None:
            continue
        deal = next((d for d in rnd.deals if d.id == v["deal_id"]), None)
        vulnerability = deal.vulnerability if deal else "None"
        pair = compute_score(
            v["contract"], v["declarer"], v["tricks_taken"], vulnerability
        )
        if pair is not None:
            ns_score, ew_score = pair
        else:
            ns_score = 0
            ew_score = 0
        key = (v["table_number"], v["deal_id"])
        rnd.results_by_table_deal[key] = Result(
            round_id=round_id,
            table_number=v["table_number"],
            deal_id=v["deal_id"],
            ns_score=ns_score,
            ew_score=ew_score,
            contract=v["contract"],
            declarer=v["declarer"],
            opening_lead=v["opening_lead"],
            tricks_taken=v["tricks_taken"],
        )
        out_results[idx] = {"ok": True, "ns_score": ns_score, "ew_score": ew_score}
        saved_count += 1

    if saved_count > 0:
        cycles = load_tournament_cycles(path)
        save_tournament(tournament, path, cycles=cycles)

    return jsonify({
        "ok": True,
        "saved": saved_count,
        "total": len(results_list),
        "results": out_results,
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
