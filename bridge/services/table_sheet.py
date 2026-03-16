"""
Table result sheet view data: one sheet per table with clear sections per round.

Each round section shows round number, NS/EW team names, and rows for each deal
(board, box/dealer/vul, contract, declarer, lead, tricks) for handwriting.
"""

from bridge.models.round_models import deal_dealer_vulnerability
from bridge.models.tournament import Tournament


def table_sheet_view_data(tournament: Tournament, table_number: int) -> dict | None:
    """
    Build data for a single table's printable result sheet.

    Returns a dict with:
      - tournament_name, tournament_date
      - table_number
      - rounds: list of {
          "round_number": int,
          "ns_name": str,
          "ew_name": str,
          "deals": [ {"id": deal_id, "box": int, "dealer": str, "vulnerability": str}, ... ]
        }
    Only rounds that contain this table are included. Returns None if the
    table never appears (e.g. invalid table_number).
    """
    team_by_id = {t.id: t.name for t in tournament.teams}
    n_boxes = tournament.number_of_boxes
    rounds_data = []
    for rnd in tournament.rounds:
        tbl = next((t for t in rnd.tables if t.table_number == table_number), None)
        if not tbl:
            continue
        ns_name = team_by_id.get(tbl.ns_team_id, "?")
        ew_name = team_by_id.get(tbl.ew_team_id, "?")
        deals_data = []
        for d in rnd.deals:
            dealer, vuln = deal_dealer_vulnerability(d.box, n_boxes)
            deals_data.append({
                "id": d.id,
                "box": d.box,
                "dealer": dealer,
                "vulnerability": vuln,
            })
        rounds_data.append({
            "round_number": rnd.round_number,
            "ns_name": ns_name,
            "ew_name": ew_name,
            "deals": deals_data,
        })
    if not rounds_data:
        return None
    return {
        "tournament_name": tournament.name,
        "tournament_date": tournament.date.isoformat(),
        "table_number": table_number,
        "rounds": rounds_data,
    }


def all_tables_sheet_data(tournament: Tournament) -> list[dict]:
    """
    Build table-sheet data for every table that appears in at least one round.

    Returns list of dicts from table_sheet_view_data, one per table_number
    (sorted by table_number). Tables that never appear are omitted.
    """
    table_numbers = set()
    for rnd in tournament.rounds:
        for tbl in rnd.tables:
            table_numbers.add(tbl.table_number)
    result = []
    for tn in sorted(table_numbers):
        data = table_sheet_view_data(tournament, tn)
        if data:
            result.append(data)
    return result
