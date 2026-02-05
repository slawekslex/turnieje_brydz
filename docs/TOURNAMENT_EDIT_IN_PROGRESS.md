# Editing tournament structure in progress

This document defines what is **allowed** vs **not allowed** when editing a tournament that already has at least one saved result (deal result in any round). The goal is to preserve data integrity and avoid invalid references while allowing safe edits.

---

## Definition: “Tournament in progress”

- **In progress** = at least one round has at least one entry in `results_by_table_deal` (i.e. at least one deal result has been saved).
- **Not in progress** = no round has any saved results. Full structure edits (e.g. current PUT that regenerates rounds from teams + cycles) are allowed and can replace the whole schedule.

Helper (for API/UI):

```python
def tournament_has_results(tournament: Tournament) -> bool:
    for rnd in tournament.rounds:
        if rnd.results_by_table_deal:
            return True
    return False
```

---

## 1. Adding a round

| Scenario | Allowed | Behaviour |
|----------|---------|-----------|
| Tournament in progress | **Yes** | Append one or more new rounds at the end. New rounds get new `round_id` and `round_number`, new table assignments (from round-robin for current team set), and new deals (next IDs in sequence). Existing rounds and all their results are unchanged. |
| Tournament not in progress | **Yes** | Same as today: can add rounds by changing cycles and regenerating, or by explicit “add round” that appends. |

**Implementation notes:**

- New round(s) must be generated with the **current** team list and (optionally) a chosen `deals_per_round` for the new round(s).
- Round IDs: use `max(r.id for r in tournament.rounds) + 1` (and increment for each new round).
- Deal IDs: use next IDs after the last deal in the tournament (e.g. last deal id in last round + 1, then +2, …).
- Validate round-robin only for the **new** rounds if you add a full cycle; if you add a single round, that round’s pairings must be valid for the current teams.

**UI:** Allow “Add round” (or “Add cycle”) only when it doesn’t remove or alter existing rounds. Show a warning if the new round changes the number of deals per round compared to an existing cycle (informational).

---

## 2. Removing a round

| Scenario | Allowed | Behaviour |
|----------|---------|-----------|
| Round has **no** saved results | **Yes** | Delete the round. Renumber subsequent rounds’ `round_number` (and optionally `id`) so there is no gap. Deals that were in the removed round are no longer in the tournament; deal IDs in other rounds stay as-is. |
| Round has **any** saved results | **No** | Do not allow removal. Reason: deleting the round would delete results and could confuse ranking/history. If we ever support it, it would be “remove round and all its results” with an explicit confirmation. |

**Recommendation:** For “in progress” tournaments, allow removing a round if the user confirms they are ok with losing the results

**UI:** “Remove round” perform a check and show a clear warning before removing

---

## 3. Changing number of deals per round

Deals are stored per round: `Round.deals` is a list; results are keyed by `(table_number, deal_id)`.

| Scenario | Allowed | Behaviour |
|----------|---------|-----------|
| Change **only for rounds that have no results yet** | **Yes** | For each such round, replace `deals` with a new list of length = new `deals_per_round`. Use deal IDs that don’t conflict (e.g. continue from current max deal id). No results to migrate. |
| **Increase** deals in a round that **already has results** | **Yes, with care** | Append new deals to `Round.deals`. New (table, deal) pairs have no result yet. Existing results unchanged. No renumbering of deal ids. |
| **Decrease** deals in a round that **already has results** | **No** (or explicit “drop results”) | Reducing the number of deals would drop some `Deal` entries; any `results_by_table_deal` for those deal ids would become orphaned or inconsistent. So: either **forbid** reducing deals when that round has any result for a deal that would be removed, or provide an explicit “reduce deals and delete results for removed deals” with confirmation. |

**Recommendation:**

- **Allow** changing deals_per_round for rounds that have **no** results (full replace of `deals` for that round).
- **Allow** **increasing** deals per round even when the round has some results (append deals only).
- **Disallow** **decreasing** deals per round when the round has at least one result for a deal that would be removed (or require an explicit “remove these deals and their results” action).

**UI:** For “deals per round”:
- If the round has no results: allow any change (with validation e.g. > 0).
- If the round has results: allow only increasing; show message that decreasing would require deleting results for the removed deals (and either disable decrease or offer a destructive action with confirmation).

---

## 4. Adding a team

| Scenario | Allowed | Behaviour |
|----------|---------|-----------|
| Tournament **not** in progress | **Yes** | Current behaviour: rebuild rounds from teams + cycles. New team gets a new id (e.g. `max(team.id)+1`). |
| Tournament **in progress** | **No** | Round-robin is defined for a fixed set of teams. Adding a team changes N; the schedule (who plays whom, number of rounds) changes. Rebuilding rounds would replace all rounds and **lose all existing results** (or require a complex remap). So adding a team when any results exist is **not allowed** unless we define a different model (e.g. “append rounds for new team” without changing existing rounds). |

**Recommendation:** **Disallow** adding a team when `tournament_has_results(tournament)` is true. Show a clear message: “Nie można dodać drużyny, gdy turniej ma już zapisane wyniki.”

**UI:** “Add team” (or plus next to teams list) disabled when tournament has any saved results; tooltip or message explains why.

---

## 5. Editing a team

Editing = changing **name** or **member names** only (team id stays the same).

| Scenario | Allowed | Behaviour |
|----------|---------|-----------|
| Change team name or member names | **Yes** | Always allowed. Only display data changes; all references use `team.id`, so rounds, table assignments, and results remain valid. |
| Change team id | **No** (treat as identity) | Team id is the stable key in `TableAssignment` and in result display. Changing id would break references. So “edit team” = edit name/members only; id is immutable. |

**Removing a team:** That would break every round that references that team (table assignments and any results at those tables). So **disallow** removing a team when the tournament is in progress (or when that team appears in any round). If we ever support it, it would be “remove team and remove/void all rounds that reference it” with strong confirmation.

**Recommendation:** **Allow** editing team name and member1/member2 names at any time. **Disallow** removing a team when the tournament has any rounds that reference that team (which is always once the schedule exists). **Disallow** changing team id.

**UI:** “Edit team” allows name and members; “Remove team” disabled once the tournament has rounds (or has results), with explanation.

---

## Summary table

| Operation | Not in progress | In progress |
|-----------|-----------------|-------------|
| **Add round** | Yes | Yes (append only) |
| **Remove round** | Yes | Only if that round has no results |
| **Change deals per round** | Yes | Yes: no results → free; has results → allow only increase (or forbid decrease / require “drop results”) |
| **Add team** | Yes | **No** |
| **Edit team** (name, members) | Yes | **Yes** |
| **Remove team** | Allowed only if no rounds reference it | **No** |
| **Change team id** | — | **No** (immutable) |

---

## Implementation checklist

1. **Helper**  
   - Add `tournament_has_results(tournament)` (and optionally `round_has_results(round)`).

2. **PUT /api/tournaments/<id>**  
   - If body would change teams (add/remove) or cycles in a way that would regenerate all rounds:  
     - If `tournament_has_results(tournament)` → return 400 with a clear message (e.g. “Nie można zmieniać liczby drużyn ani struktury cykli, gdy turniej ma zapisane wyniki.”).  
   - If only name, date, or team **edits** (same number of teams, same ids, only name/members):  
     - Apply name/date; apply team name/member changes; **do not** regenerate rounds. Save. Return 200.

3. **Add round**  
   - New endpoint or extended API: e.g. POST `/api/tournaments/<id>/rounds` with optional `deals_per_round` and `count`. Append new round(s), assign deals, save. Never remove or renumber existing rounds in this flow.

4. **Remove round**  
   - New endpoint: e.g. DELETE `/api/tournaments/<id>/rounds/<round_id>`.  
   - If that round has any results → 400 (or 409) with message.  
   - Else remove round, renumber `round_number` (and optionally `id`) of following rounds, save.

5. **Change deals per round**  
   - Can be part of “edit round” or “edit cycle”:  
     - For rounds with no results: set new deals list.  
     - For rounds with results: allow only adding deals (append); reject or special-flow when reducing.

6. **UI**  
   - Use `tournament_has_results` (or round-level flags) to enable/disable “Add team”, “Remove round”, “Remove team”, and to show appropriate messages or confirmations for destructive or restricted operations.

---

## Optional future extensions

- **Remove round with results:** Allow with confirmation and delete all results for that round; then remove the round.
- **Decrease deals in a round with results:** Explicit action “Remove last N deals and their results” with confirmation.
- **Add team in progress:** Define “append-only” mode: keep all existing rounds and results; generate extra round(s) so the new team plays everyone once (different schedule model; more complex).

These are not required for the first version of “edit in progress” behaviour.
