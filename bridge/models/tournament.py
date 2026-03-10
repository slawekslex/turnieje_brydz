"""
Tournament container and JSON serialization.

Encapsulates teams, round structures, round results, name and date.
Persistence (save/load to disk) lives in bridge.storage.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List

from bridge.models.round_models import (
    Deal,
    Result,
    Round,
    TableAssignment,
    Team,
    TeamMember,
    box_for_deal,
)


@dataclass
class Tournament:
    """
    A bridge tournament: name, date, all teams, and rounds
    (structure + deals + results). number_of_boxes is how many
    boxes are used for deals.
    """

    name: str
    date: date
    teams: List[Team]
    rounds: List[Round]
    number_of_boxes: int = 1

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tournament name must be non-empty")
        if self.number_of_boxes < 1:
            raise ValueError("number_of_boxes must be at least 1")


# --- Serialization helpers (round_models -> JSON-serializable dict) ---


def _team_member_to_dict(m: TeamMember) -> Dict[str, Any]:
    return {"name": m.name}


def _team_member_from_dict(d: Dict[str, Any]) -> TeamMember:
    return TeamMember(name=d["name"])


def _team_to_dict(t: Team) -> Dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "member1": _team_member_to_dict(t.member1),
        "member2": _team_member_to_dict(t.member2),
    }


def _team_from_dict(d: Dict[str, Any]) -> Team:
    return Team(
        id=d["id"],
        name=d["name"],
        member1=_team_member_from_dict(d["member1"]),
        member2=_team_member_from_dict(d["member2"]),
    )


def _deal_to_dict(deal: Deal) -> Dict[str, Any]:
    return {"id": deal.id, "box": deal.box}


def _deal_from_dict(d: Dict[str, Any], number_of_boxes: int = 1) -> Deal:
    number_of_boxes = max(1, number_of_boxes)
    if "box" in d:
        return Deal(id=d["id"], box=max(1, int(d["box"])))
    # Backward compatibility: old format had number, dealer, vulnerability
    board_number = d.get("number") or d["id"]
    box = box_for_deal(int(board_number), number_of_boxes)
    return Deal(id=d["id"], box=box)


def _table_assignment_to_dict(ta: TableAssignment) -> Dict[str, Any]:
    return {
        "table_number": ta.table_number,
        "ns_team_id": ta.ns_team_id,
        "ew_team_id": ta.ew_team_id,
    }


def _table_assignment_from_dict(d: Dict[str, Any]) -> TableAssignment:
    return TableAssignment(
        table_number=d["table_number"],
        ns_team_id=d["ns_team_id"],
        ew_team_id=d["ew_team_id"],
    )


def _result_to_dict(r: Result) -> Dict[str, Any]:
    out = {
        "round_id": r.round_id,
        "table_number": r.table_number,
        "deal_id": r.deal_id,
        "ns_score": r.ns_score,
        "ew_score": r.ew_score,
        "contract": r.contract or "",
        "declarer": r.declarer or "",
        "opening_lead": r.opening_lead or "",
    }
    if r.tricks_taken is not None:
        out["tricks_taken"] = r.tricks_taken
    return out


def _result_from_dict(d: Dict[str, Any]) -> Result:
    return Result(
        round_id=d["round_id"],
        table_number=d["table_number"],
        deal_id=d["deal_id"],
        ns_score=d.get("ns_score", 0),
        ew_score=d.get("ew_score", 0),
        contract=d.get("contract", ""),
        declarer=d.get("declarer", ""),
        opening_lead=d.get("opening_lead", ""),
        tricks_taken=d.get("tricks_taken"),
    )


def _results_by_table_deal_to_dict(
    results_by_table_deal: Dict[tuple, Result],
) -> Dict[str, Dict[str, Any]]:
    """Convert (table_number, deal_id) -> Result to JSON-serializable dict."""
    out: Dict[str, Dict[str, Any]] = {}
    for (table_number, deal_id), result in results_by_table_deal.items():
        key = f"{table_number},{deal_id}"
        out[key] = _result_to_dict(result)
    return out


def _results_by_table_deal_from_dict(
    d: Dict[str, Dict[str, Any]],
) -> Dict[tuple, Result]:
    out: Dict[tuple, Result] = {}
    for key, val in d.items():
        table_number_str, deal_id_str = key.split(",", 1)
        table_number = int(table_number_str)
        deal_id = int(deal_id_str)
        out[(table_number, deal_id)] = _result_from_dict(val)
    return out


def _round_to_dict(rnd: Round) -> Dict[str, Any]:
    return {
        "id": rnd.id,
        "round_number": rnd.round_number,
        "tables": [_table_assignment_to_dict(t) for t in rnd.tables],
        "deals": [_deal_to_dict(d) for d in rnd.deals],
        "results_by_table_deal": _results_by_table_deal_to_dict(
            rnd.results_by_table_deal
        ),
    }


def _round_from_dict(d: Dict[str, Any], number_of_boxes: int = 1) -> Round:
    return Round(
        id=d["id"],
        round_number=d["round_number"],
        tables=[_table_assignment_from_dict(t) for t in d["tables"]],
        deals=[_deal_from_dict(de, number_of_boxes) for de in d["deals"]],
        results_by_table_deal=_results_by_table_deal_from_dict(
            d["results_by_table_deal"]
        ),
    )


def tournament_to_dict(t: Tournament) -> Dict[str, Any]:
    """Convert a Tournament to a JSON-serializable dict."""
    return {
        "name": t.name,
        "date": t.date.isoformat(),
        "teams": [_team_to_dict(team) for team in t.teams],
        "rounds": [_round_to_dict(rnd) for rnd in t.rounds],
        "number_of_boxes": t.number_of_boxes,
    }


def tournament_from_dict(d: Dict[str, Any]) -> Tournament:
    """Build a Tournament from a dict (e.g. loaded from JSON)."""
    number_of_boxes = max(1, int(d.get("number_of_boxes", 1)))
    return Tournament(
        name=d["name"],
        date=date.fromisoformat(d["date"]),
        teams=[_team_from_dict(t) for t in d["teams"]],
        rounds=[_round_from_dict(r, number_of_boxes) for r in d["rounds"]],
        number_of_boxes=number_of_boxes,
    )
