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
      - "byes": list of {"team_name"} for teams not playing this round (opponent = BYE)
    Team names are resolved from tournament.teams; missing IDs show as "?".
    """
    team_by_id = {t.id: t.name for t in tournament.teams}
    all_team_ids = set(team_by_id)
    schedule = []
    for rnd in tournament.rounds:
        tables = []
        playing_ids = set()
        for tbl in sorted(rnd.tables, key=lambda x: x.table_number):
            playing_ids.add(tbl.ns_team_id)
            playing_ids.add(tbl.ew_team_id)
            ns_name = team_by_id.get(tbl.ns_team_id, "?")
            ew_name = team_by_id.get(tbl.ew_team_id, "?")
            tables.append({
                "table_number": tbl.table_number,
                "ns_name": ns_name,
                "ew_name": ew_name,
            })
        bye_ids = all_team_ids - playing_ids
        byes = [{"team_name": team_by_id[tid]} for tid in sorted(bye_ids)]
        schedule.append({
            "round_number": rnd.round_number,
            "tables": tables,
            "byes": byes,
        })
    return schedule
