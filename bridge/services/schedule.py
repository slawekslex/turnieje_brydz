"""
Schedule view data: build round/table list for the schedule page.
"""

from bridge.models.tournament import Tournament


def schedule_view_data(tournament: Tournament) -> list:
    """
    Build schedule data for the tournament schedule page.

    Returns a list of dicts, one per round:
      - "round_number": int
      - "tables": list of {"table_number", "ns_name", "ns_players", "ew_name", "ew_players"}
      - "byes": list of {"team_name", "team_players"} for teams not playing this round (opponent = BYE)
    Team names and player names (member1, member2) are resolved from tournament.teams; missing IDs show as "?".
    """
    team_by_id = {t.id: t for t in tournament.teams}
    all_team_ids = set(team_by_id)
    schedule = []
    for rnd in tournament.rounds:
        tables = []
        playing_ids = set()
        for tbl in sorted(rnd.tables, key=lambda x: x.table_number):
            playing_ids.add(tbl.ns_team_id)
            playing_ids.add(tbl.ew_team_id)
            ns_team = team_by_id.get(tbl.ns_team_id)
            ew_team = team_by_id.get(tbl.ew_team_id)
            ns_name = ns_team.name if ns_team else "?"
            ew_name = ew_team.name if ew_team else "?"
            ns_players = f"{ns_team.member1.name}, {ns_team.member2.name}" if ns_team else ""
            ew_players = f"{ew_team.member1.name}, {ew_team.member2.name}" if ew_team else ""
            tables.append({
                "table_number": tbl.table_number,
                "ns_name": ns_name,
                "ns_players": ns_players,
                "ew_name": ew_name,
                "ew_players": ew_players,
            })
        bye_ids = all_team_ids - playing_ids
        byes = []
        for tid in sorted(bye_ids):
            team = team_by_id.get(tid)
            if team:
                byes.append({
                    "team_name": team.name,
                    "team_players": f"{team.member1.name}, {team.member2.name}",
                })
            else:
                byes.append({"team_name": "?", "team_players": ""})
        schedule.append({
            "round_number": rnd.round_number,
            "tables": tables,
            "byes": byes,
        })
    return schedule
