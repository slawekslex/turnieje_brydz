"""
Build deal-by-deal results view data for a round (with IMPs).
"""

from bridge.scoring import calculate_deal_imp_scores
from bridge.models.tournament import Tournament


def round_results_view_data(tournament: Tournament, round_id: int):
    """
    Build deal-by-deal results with IMPs for a round.
    Returns (round, deals_with_tables) or (None, None) if round not found.
    """
    rnd = next((r for r in tournament.rounds if r.id == round_id), None)
    if not rnd:
        return None, None
    team_by_id = {t.id: t.name for t in tournament.teams}
    tables_sorted = sorted(rnd.tables, key=lambda t: t.table_number)
    deals_with_tables = []
    for d in rnd.deals:
        rows = []
        ns_scores = []
        for tbl in tables_sorted:
            res = rnd.results_by_table_deal.get((tbl.table_number, d.id))
            ns_name = team_by_id.get(tbl.ns_team_id, "?")
            ew_name = team_by_id.get(tbl.ew_team_id, "?")
            if res:
                rows.append({
                    "table_number": tbl.table_number,
                    "ns_team": ns_name,
                    "ew_team": ew_name,
                    "contract": res.contract or "—",
                    "declarer": res.declarer or "—",
                    "opening_lead": res.opening_lead or "—",
                    "tricks_taken": res.tricks_taken if res.tricks_taken is not None else "—",
                    "ns_score": res.ns_score,
                    "ew_score": res.ew_score,
                })
                ns_scores.append(res.ns_score)
            else:
                rows.append({
                    "table_number": tbl.table_number,
                    "ns_team": ns_name,
                    "ew_team": ew_name,
                    "contract": "—",
                    "declarer": "—",
                    "opening_lead": "—",
                    "tricks_taken": "—",
                    "ns_score": None,
                    "ew_score": None,
                })
        if len(ns_scores) == len(rows) and ns_scores:
            imps = calculate_deal_imp_scores(ns_scores)
            for i, row in enumerate(rows):
                row["ns_imp"] = imps[i][0]
                row["ew_imp"] = imps[i][1]
        else:
            for row in rows:
                row["ns_imp"] = None
                row["ew_imp"] = None
        deals_with_tables.append({"deal": d, "table_rows": rows})
    return rnd, deals_with_tables


def round_ranking_data(tournament: Tournament, round_id: int):
    """
    Build cumulative IMP ranking including all rounds with round_number <= this round.
    Returns (round, ranking_list, round_numbers, None) or (round, None, None, error_message).
    ranking_list is [ {"team_name": str, "total_imp": int, "round_imps": [int, ...]}, ... ]
    sorted by total_imp desc. round_numbers is [1, 2, ...] for column headers.
    """
    rnd = next((r for r in tournament.rounds if r.id == round_id), None)
    if not rnd:
        return None, None, None, "Round not found"
    rounds_to_include = [r for r in tournament.rounds if r.round_number <= rnd.round_number]
    round_numbers = [r.round_number for r in rounds_to_include]
    # Collect all team names that appear in any round (for byes we use 0)
    all_teams = set()
    per_round_imps = []  # list of dicts: [{team: imp}, ...] one per round
    for r in rounds_to_include:
        _, deals_with_tables = round_results_view_data(tournament, r.id)
        round_imp_for_team = {}
        for item in deals_with_tables:
            for row in item.get("table_rows") or []:
                ns_imp = row.get("ns_imp")
                ew_imp = row.get("ew_imp")
                if ns_imp is None or ew_imp is None:
                    return rnd, None, None, "Not all results saved for rounds 1–" + str(rnd.round_number)
                ns_team = (row.get("ns_team") or "").strip() or "?"
                ew_team = (row.get("ew_team") or "").strip() or "?"
                round_imp_for_team[ns_team] = round_imp_for_team.get(ns_team, 0) + ns_imp
                round_imp_for_team[ew_team] = round_imp_for_team.get(ew_team, 0) + ew_imp
                all_teams.add(ns_team)
                all_teams.add(ew_team)
        per_round_imps.append(round_imp_for_team)
    team_imps = {}
    team_round_imps = {}
    for name in all_teams:
        round_imps = [per_round_imps[i].get(name, 0) for i in range(len(round_numbers))]
        total = sum(round_imps)
        team_imps[name] = total
        team_round_imps[name] = round_imps
    ranking = [
        {
            "team_name": name,
            "total_imp": total,
            "round_imps": team_round_imps[name],
        }
        for name, total in sorted(team_imps.items(), key=lambda x: -x[1])
    ]
    return rnd, ranking, round_numbers, None


def round_head_to_head_data(tournament: Tournament, round_id: int):
    """
    Build head-to-head IMP matrix: for each pair (team_a, team_b), the total IMP
    that team_a scored when playing against team_b (cumulative up to this round).
    Returns (round, error_message or None, team_names, matrix).
    matrix[i][j] = IMP that team_names[i] scored vs team_names[j]; diagonal = 0.
    """
    rnd = next((r for r in tournament.rounds if r.id == round_id), None)
    if not rnd:
        return None, "Round not found", [], []
    rounds_to_include = [r for r in tournament.rounds if r.round_number <= rnd.round_number]
    # h2h[team_a][team_b] = IMP that team_a scored when playing vs team_b
    h2h: dict[str, dict[str, int]] = {}
    for r in rounds_to_include:
        _, deals_with_tables = round_results_view_data(tournament, r.id)
        # Per table (same NS/EW across deals), sum ns_imp and ew_imp over deals
        tables_by_num: dict[int, dict] = {}
        for item in deals_with_tables:
            for row in item.get("table_rows") or []:
                tn = row.get("table_number")
                ns_imp = row.get("ns_imp")
                ew_imp = row.get("ew_imp")
                if ns_imp is None or ew_imp is None:
                    return rnd, "Not all results saved for rounds 1–" + str(rnd.round_number), [], []
                ns_team = (row.get("ns_team") or "").strip() or "?"
                ew_team = (row.get("ew_team") or "").strip() or "?"
                if tn not in tables_by_num:
                    tables_by_num[tn] = {"ns_team": ns_team, "ew_team": ew_team, "ns_imp": 0, "ew_imp": 0}
                tables_by_num[tn]["ns_imp"] += ns_imp
                tables_by_num[tn]["ew_imp"] += ew_imp
        for t in tables_by_num.values():
            na, ea = t["ns_team"], t["ew_team"]
            if na not in h2h:
                h2h[na] = {}
            if ea not in h2h:
                h2h[ea] = {}
            h2h[na][ea] = h2h[na].get(ea, 0) + t["ns_imp"]
            h2h[ea][na] = h2h[ea].get(na, 0) + t["ew_imp"]
    team_names = sorted(h2h.keys())
    n = len(team_names)
    idx = {name: i for i, name in enumerate(team_names)}
    matrix = [[0] * n for _ in range(n)]
    for i, name_i in enumerate(team_names):
        for name_j, imp in (h2h.get(name_i) or {}).items():
            j = idx.get(name_j)
            if j is not None:
                matrix[i][j] = imp
    return rnd, None, team_names, matrix
