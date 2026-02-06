"""
Schedule view data: build round/table list for the schedule page.
"""

from bridge.models.tournament import Tournament


def schedule_view_data(tournament: Tournament) -> list:
    """
    Build schedule data for the tournament schedule page.

    Returns a list of dicts, one per round:
      - "round_number": int
      - "tables": list of {"table_number", "ns_name", "ew_name"}
    Team names are resolved from tournament.teams; missing IDs show as "?".
    """
    team_by_id = {t.id: t.name for t in tournament.teams}
    schedule = []
    for rnd in tournament.rounds:
        tables = []
        for tbl in sorted(rnd.tables, key=lambda x: x.table_number):
            ns_name = team_by_id.get(tbl.ns_team_id, "?")
            ew_name = team_by_id.get(tbl.ew_team_id, "?")
            tables.append({
                "table_number": tbl.table_number,
                "ns_name": ns_name,
                "ew_name": ew_name,
            })
        schedule.append({
            "round_number": rnd.round_number,
            "tables": tables,
        })
    return schedule
