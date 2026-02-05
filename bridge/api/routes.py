"""
Flask API: pages and REST endpoints for tournaments, rounds, settings.
"""

import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, render_template

from bridge.models.contract import (
    CONTRACT_LEVELS,
    CONTRACT_MODIFIERS,
    CONTRACT_PATTERN,
    CONTRACT_SUITS,
)
from bridge.scoring import compute_score
from bridge.models.round_models import Result
from bridge.models.tournament import Tournament
from bridge.services.round_results import round_results_view_data
from bridge.services.tournament_service import parse_tournament_payload
from bridge.storage import (
    ensure_data_dir,
    ensure_tournament_dir,
    get_tournament_data_path,
    list_tournament_entries,
    load_settings,
    load_tournament,
    load_tournament_cycles,
    save_settings,
    save_tournament,
    tournament_folder_name,
)
from bridge.validation import validate_result_complete, validate_result_fields

bp = Blueprint("api", __name__, url_prefix="")


def _data_dir() -> Path:
    return Path(current_app.config["DATA_DIR"])


def _tournament_path(tour_id: str) -> Path | None:
    return get_tournament_data_path(_data_dir(), tour_id)


# --- Pages ---

@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/tournament/<tour_id>")
def tournament_edit_page(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return render_template("404.html"), 404
    return render_template("tournament_edit.html", tour_id=tour_id)


@bp.route("/tournament/<tour_id>/rounds")
def tournament_rounds_page(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return render_template("404.html"), 404
    return render_template("tournament_rounds.html", tour_id=tour_id)


@bp.route("/tournament/<tour_id>/rounds/<int:round_id>/ranking")
def round_ranking_placeholder(tour_id: str, round_id: int):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return render_template("404.html"), 404
    return render_template(
        "placeholder.html",
        tour_id=tour_id,
        title="Ranking",
        message="Strona „Ranking” będzie dostępna w kolejnej wersji.",
    )


# --- Settings ---

@bp.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(load_settings(_data_dir()))


@bp.route("/api/settings", methods=["PATCH"])
def update_settings():
    body = request.get_json(force=True, silent=True) or {}
    allowed = {"debug_mode"}
    updates = {k: v for k, v in body.items() if k in allowed and isinstance(v, bool)}
    if not updates:
        return jsonify(load_settings(_data_dir()))
    save_settings(_data_dir(), updates)
    return jsonify(load_settings(_data_dir()))


# --- Tournaments ---

@bp.route("/api/tournaments", methods=["GET"])
def list_tournaments():
    entries = list_tournament_entries(_data_dir())
    active = [e for e in entries if not e.get("archived")]
    return jsonify(active)


@bp.route("/api/tournaments/<tour_id>", methods=["GET"])
def get_tournament(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return jsonify({"error": "Not found"}), 404
    tournament = load_tournament(path)
    teams_data = [
        {"name": t.name, "member1": t.member1.name, "member2": t.member2.name}
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


@bp.route("/api/tournaments/<tour_id>/rounds", methods=["GET"])
def get_tournament_rounds(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
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
                    results_by_deal[str(d.id)] = {
                        "contract": "", "declarer": "", "opening_lead": "",
                        "tricks_taken": None, "ns_score": 0, "ew_score": 0,
                    }
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


@bp.route("/api/tournaments/<tour_id>/rounds/<int:round_id>/deal-results", methods=["GET"])
def get_round_deal_results(tour_id: str, round_id: int):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return jsonify({"error": "Not found"}), 404
    tournament = load_tournament(path)
    rnd, deals_with_tables = round_results_view_data(tournament, round_id)
    if not rnd:
        return jsonify({"error": "Round not found"}), 404
    out = [
        {
            "deal": {"number": item["deal"].number, "dealer": item["deal"].dealer, "vulnerability": item["deal"].vulnerability},
            "table_rows": item["table_rows"],
        }
        for item in deals_with_tables
    ]
    return jsonify({"deals_with_tables": out})


# --- Contract spec ---

@bp.route("/api/contract-spec", methods=["GET"])
def contract_spec():
    return jsonify({
        "levels": list(CONTRACT_LEVELS),
        "suits": list(CONTRACT_SUITS),
        "modifiers": [m for m in CONTRACT_MODIFIERS if m],
        "pattern": CONTRACT_PATTERN.pattern,
    })


# --- Result validation ---

def _parse_tricks(raw):
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@bp.route("/api/validate-result", methods=["POST"])
def validate_result():
    body = request.get_json(force=True, silent=True) or {}
    contract = (body.get("contract") or "").strip()
    declarer = (body.get("declarer") or "").strip().upper()
    opening_lead = (body.get("opening_lead") or "").strip()
    vulnerability = (body.get("vulnerability") or "").strip() or "None"
    tricks_taken = _parse_tricks(body.get("tricks_taken"))

    errors = validate_result_complete(contract, declarer, opening_lead, tricks_taken)
    if not errors:
        errors = validate_result_fields(contract, declarer, opening_lead, tricks_taken)
    if errors:
        return jsonify({"valid": False, "errors": errors})

    pair = compute_score(contract, declarer, tricks_taken, vulnerability)
    if pair is None:
        return jsonify({"valid": True, "ns_score": 0, "ew_score": 0})
    ns_score, ew_score = pair
    return jsonify({"valid": True, "ns_score": ns_score, "ew_score": ew_score})


# --- Save round results ---

@bp.route("/api/tournaments/<tour_id>/round-results", methods=["POST"])
def save_round_results(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(force=True, silent=True) or {}
    round_id = body.get("round_id")
    results_list = body.get("results") or []
    if round_id is None:
        return jsonify({"error": "round_id required"}), 400
    round_id = int(round_id)

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
        tricks_taken = _parse_tricks(item.get("tricks_taken"))

        errs = validate_result_complete(contract, declarer, opening_lead, tricks_taken)
        if not errs:
            errs = validate_result_fields(contract, declarer, opening_lead, tricks_taken)
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
            out_results.append(None)

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
        pair = compute_score(v["contract"], v["declarer"], v["tricks_taken"], vulnerability)
        ns_score, ew_score = (pair if pair is not None else (0, 0))
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
        save_tournament(tournament, path, cycles=load_tournament_cycles(path))

    return jsonify({
        "ok": True,
        "saved": saved_count,
        "total": len(results_list),
        "results": out_results,
    })


# --- Create / update tournament ---

@bp.route("/api/tournaments", methods=["POST"])
def create_tournament():
    ensure_data_dir(_data_dir())
    body = request.get_json(force=True, silent=True) or {}
    data, errors = parse_tournament_payload(body)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    name, tournament_date, teams, cycles, rounds = data

    tournament = Tournament(name=name, date=tournament_date, teams=teams, rounds=rounds)
    tour_id = str(uuid.uuid4())
    data_dir = _data_dir()
    date_str = body.get("date") or ""
    folder = tournament_folder_name(name, date_str, tour_id, data_dir)
    ensure_tournament_dir(data_dir, folder)
    path = data_dir / folder / "data.json"
    save_tournament(tournament, path, cycles=cycles, tour_id=tour_id)

    return jsonify({"ok": True, "id": tour_id, "name": name, "date": date_str})


@bp.route("/api/tournaments/<tour_id>/archive", methods=["POST"])
def archive_tournament(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return jsonify({"ok": False, "error": "Not found"}), 404
    tournament = load_tournament(path)
    save_tournament(tournament, path, cycles=load_tournament_cycles(path), archived=True)
    return jsonify({"ok": True})


@bp.route("/api/tournaments/<tour_id>", methods=["PUT"])
def update_tournament(tour_id: str):
    path = _tournament_path(tour_id)
    if not path or not path.exists():
        return jsonify({"ok": False, "errors": ["Turniej nie istnieje."]}), 404
    body = request.get_json(force=True, silent=True) or {}
    data, errors = parse_tournament_payload(body)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    name, tournament_date, teams, cycles, rounds = data

    tournament = Tournament(name=name, date=tournament_date, teams=teams, rounds=rounds)
    save_tournament(tournament, path, cycles=cycles)
    date_str = body.get("date") or ""
    return jsonify({"ok": True, "id": tour_id, "name": name, "date": date_str})
