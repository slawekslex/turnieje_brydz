# Rounds page – simplification suggestions

## 1. REMOVE

### Standalone “Wyniki rozdań” page
- **What:** `round_results_page` route and `templates/round_results.html`.
- **Why:** Wyniki are now shown inline on the rounds page. The standalone URL is only useful for direct links/bookmarks; you can drop it to have one less route and one less template.
- **If you keep it:** Consider redirecting `/rounds/<id>/results` → rounds page with that round in view mode (so bookmarks still work).

### Unused CSS
- **`.schedule-page`**, **`.schedule-card`**, **`.schedule-meta`** – Template uses `rounds-page`, `rounds-card`, `rounds-meta`. Remove the `schedule-*` variants if nothing references them, or keep a single set (e.g. only `rounds-*`).
- **`.round-complete-actions`** – The old “Wyniki rozdań / Ranking” block was replaced by `round-view-actions`. Remove the unused class.

---

## 2. STREAMLINE / REUSE

### Single round header (no duplicate title)
- **What:** Edit and view modes each have their own `round-detail-title` and `round-detail-caption` (edit: `#round-detail-title`, `#round-detail-caption`; view: `#round-detail-title-view`, `#round-detail-caption-view`). Both are updated in `setRound()`.
- **Change:** Use **one** header for the round (one `<h2>`, one caption) that stays visible in both modes. Only the content below (edit panel vs view panel) switches. Then you update one title and one caption, and avoid duplicate IDs.

### Backend: one source for deal results
- **What:** `_round_results_view_data()` is used by:
  - `get_round_deal_results()` (JSON API for inline wyniki)
  - `round_results_page()` (standalone HTML page)
- **If you remove the standalone page:** You only need the JSON API and `_round_results_view_data`. No change to the helper itself.

### Score formatting
- **What:** `formatScore(ns, ew, declarer)` for edit UI (e.g. "NS +120"); `formatScoreSigned(n)` for wyniki table (e.g. "+2", "—").
- **Change:** Keep both but add a one-line comment above each: “Edit UI: NS/EW + points” vs “Wyniki table: signed number or —”. No need to unify.

---

## 3. SIMPLIFY (JS)

### One function to switch mode
- **What:** `showEditMode()` and `showViewMode()` each toggle `.hidden` on the two panels.
- **Change:** Replace with one `setRoundPanel(mode)` (or `showPanel('edit' | 'view')`) that shows the right panel and hides the other. Cuts a few lines and one concept.

### Inline `setViewModeLinks`
- **What:** `setViewModeLinks()` only sets `linkRoundRanking.href` for the current round.
- **Change:** Inline that logic where you call it (in `setRound` when entering view mode and after save when switching to view). Then remove the function. Only one call site.

### Rename `schedule` → `roundsData` (or `tournamentRounds`)
- **What:** Variable `schedule` holds the GET /rounds response (name, date, rounds).
- **Change:** Rename to e.g. `roundsData` so it’s clear it’s “rounds payload”, not “schedule” in the UI sense. Optional but improves readability.

### Tab/Enter keydown: extract “focus next/prev row”
- **What:** The `tablesList` keydown handler has two big blocks for Tab (prev/next) and one for Enter, with repeated logic: find next/prev row, maybe expand card, focus first/last input.
- **Change:** Extract e.g. `focusRowInput(row, direction)` where `direction` is 'next' or 'prev'. Handler then becomes: on Tab → `focusRowInput(row, e.shiftKey ? 'prev' : 'next')`; on Enter → `focusRowInput(row, 'next')`. Shorter and easier to change later.

### Wyniki HTML: optional small template
- **What:** `renderWynikiInline()` builds a long HTML string for deal sections and tables.
- **Change:** Option A – keep as is, add a short comment “Builds deal-results-section + table per deal”. Option B – add a `<template id="wyniki-deal-tpl">` in the HTML with one deal’s structure and fill it in JS (clone, set textContent). Only worth it if you want to avoid string concatenation; current approach is fine for maintainability.

---

## 4. TEMPLATE

### Single round header (see above)
- One `<div class="round-detail-header">` with one `<h2>` and one `<span>` for caption, outside the edit/view panels, so it’s always visible when a round is selected.

### Optional: combine “round-view-message” and wyniki container
- **What:** “Wszystkie rozdania zapisane.” and then `#round-view-wyniki`.
- **Change:** You could put the message inside `#round-view-wyniki` as the first child and replace it when wyniki load. Not necessary; current structure is clear.

---

## 5. SUMMARY TABLE

| Item | Action | Impact |
|------|--------|--------|
| Standalone round_results page | Remove (or redirect) | Less code, one place for wyniki |
| schedule-* / round-complete-actions CSS | Remove if unused | Cleaner CSS |
| Duplicate round title/caption | Single header | Less DOM, simpler setRound |
| showEditMode + showViewMode | One setRoundPanel(mode) | Clearer API |
| setViewModeLinks | Inline | One less function |
| schedule → roundsData | Rename | Clarity |
| Tab/Enter keydown | focusRowInput helper | Shorter, clearer |

---

## 6. IMPLEMENTED

### First pass
- **Single round header:** One `<h2>` and caption; edit actions (Zapisz rundę, Auto, status) and view actions (Ranking, Edycja) are in two spans in the same header, toggled with the panel.
- **setRoundPanel(mode):** Replaced `showEditMode()` / `showViewMode()` with one `setRoundPanel('edit' | 'view')` that toggles both content panels and both action spans.
- **Removed duplicate title/caption:** No more `round-detail-title-view` / `round-detail-caption-view`.
- **Removed unused CSS:** `.schedule-page`, `.schedule-card`, `.schedule-meta`; `.round-complete-actions`, `.round-view-actions`. Replaced with `.round-detail-actions` for the header action spans.

### Second pass (other improvements)
- **Standalone wyniki page:** Removed `round_results.html`. Route `/tournament/<id>/rounds/<round_id>/results` now redirects to the rounds page with `?round=<round_id>`. Rounds page reads `?round=` on load and selects that round (so bookmarks/open links still work).
- **schedule → roundsData:** Renamed everywhere; **scheduleHasUnsavedChanges → roundsHasUnsavedChanges**.
- **setRankingLink inlined:** Removed the helper; the two call sites set `linkRoundRanking.href` directly.
- **focusAdjacentRowInput(row, direction):** Extracted Tab/Enter logic into `focusAdjacentRowInput(row, 'next' | 'prev')`; keydown handler is now a short Tab/Enter branch.
- **Comments:** Added one-line comments for `formatScore` (edit UI), `formatScoreSigned` (wyniki table), and `renderWynikiInline` (builds deal-results sections).
