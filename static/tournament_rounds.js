(function () {
  const tourId = window.TOUR_ID;
  const roundsContent = document.getElementById('rounds-content');
  const loadError = document.getElementById('load-error');
  const tournamentTitle = document.getElementById('tournament-title');
  const roundsMeta = document.getElementById('rounds-meta');
  const roundsList = document.getElementById('rounds-list');
  const roundDetailTitle = document.getElementById('round-detail-title');
  const roundDetailCaption = document.getElementById('round-detail-caption');
  const tablesList = document.getElementById('tables-list');
  const linkEdit = document.getElementById('link-edit');
  const btnSaveRound = document.getElementById('btn-save-round');
  const btnAutoRound = document.getElementById('btn-auto-round');
  const saveRoundStatus = document.getElementById('save-round-status');
  const tabWyniki = document.getElementById('tab-wyniki');
  const tabRanking = document.getElementById('tab-ranking');
  const tabHead2Head = document.getElementById('tab-head2head');
  const roundDetailEdit = document.getElementById('round-detail-edit');
  const roundDetailView = document.getElementById('round-detail-view');
  const roundDetailEditActions = document.getElementById('round-detail-edit-actions');
  const roundDetailViewActions = document.getElementById('round-detail-view-actions');
  const btnRoundEdit = document.getElementById('btn-round-edit');
  const roundViewWyniki = document.getElementById('round-view-wyniki');
  const roundViewRankingActions = document.getElementById('round-view-ranking-actions');
  const btnRankingPrint = document.getElementById('btn-ranking-print');
  const btnRankingExport = document.getElementById('btn-ranking-export');

  let roundsData = null;
  let lastRankingData = null;
  let selectedRoundIndex = 0;
  let roundsHasUnsavedChanges = false;
  let roundViewMode = 'edit'; // 'edit' | 'view'
  let viewTab = 'wyniki'; // 'wyniki' | 'ranking' | 'head2head' (when in view mode)
  const DEFAULT_OPENING_LEAD = '—';

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function normalizeOpeningLead(lead) {
    var value = (lead || '').toString().trim();
    return value === '' ? DEFAULT_OPENING_LEAD : value;
  }

  /** Build HTML for the shared box-info block: box number (blue), dealer, NS/EW vul. */
  function buildBoxInfoHtml(boxNum, dealer, vulnerability) {
    var vul = (vulnerability || 'None').trim();
    var nsVul = vul === 'N-S' || vul === 'Both';
    var ewVul = vul === 'E-W' || vul === 'Both';
    var num = boxNum != null && boxNum !== '' ? escapeHtml(String(boxNum)) : '—';
    var dealerStr = (dealer || '').trim() ? escapeHtml(String(dealer)) : '—';
    return '<span class="box-info">' +
      '<span class="box-info__num">' + num + '</span>' +
      '<span class="box-info__dealer">' + dealerStr + '</span>' +
      '<span class="box-info__vul">' +
      '<span class="vul-seg vul-ns' + (nsVul ? ' vul-vul' : ' vul-nv') + '">NS</span>' +
      '<span class="vul-seg vul-ew' + (ewVul ? ' vul-vul' : ' vul-nv') + '">EW</span>' +
      '</span></span>';
  }

  function setDealRowStateFromValidation(rowEl, valid, errors) {
    if (!rowEl) return;
    var contractErr = rowEl.querySelector('.deal-contract-error');
    var declarerErr = rowEl.querySelector('.deal-declarer-error');
    var leadErr = rowEl.querySelector('.deal-lead-error');
    var tricksErr = rowEl.querySelector('.deal-tricks-error');
    [contractErr, declarerErr, leadErr, tricksErr].forEach(function (el) {
      if (el) { el.textContent = ''; el.classList.add('hidden'); }
    });
    if (errors && errors.length) {
      errors.forEach(function (e) {
        var el = e.field === 'contract' ? contractErr : e.field === 'declarer' ? declarerErr : e.field === 'opening_lead' ? leadErr : e.field === 'tricks_taken' ? tricksErr : null;
        if (el) { el.textContent = e.message; el.classList.remove('hidden'); }
      });
    }
    rowEl.classList.remove('deal-row--empty', 'deal-row--valid', 'deal-row--invalid');
    if (valid === true) rowEl.classList.add('deal-row--valid');
    else if (valid === false) rowEl.classList.add('deal-row--invalid');
    else if (valid === 'empty') rowEl.classList.add('deal-row--empty');
  }

  /** Edit UI: show NS/EW and points (e.g. "NS +120"). */
  function formatScore(nsScore, ewScore, declarer) {
    var ns = parseInt(nsScore, 10) || 0;
    var ew = parseInt(ewScore, 10) || 0;
    var decl = (declarer || '').toString().trim().toUpperCase();
    if (decl === 'E' || decl === 'W') {
      return ew !== 0 ? 'EW ' + (ew > 0 ? '+' : '') + ew : '—';
    }
    if (decl === 'N' || decl === 'S') {
      return ns !== 0 ? 'NS ' + (ns > 0 ? '+' : '') + ns : '—';
    }
    if (ns !== 0) return 'NS ' + (ns > 0 ? '+' : '') + ns;
    if (ew !== 0) return 'EW ' + (ew > 0 ? '+' : '') + ew;
    return '—';
  }

  /** True if every deal has all fields filled and backend-validated (has scores). */
  function tableAllResultsFilledAndValidated(table, deals) {
    if (!deals || !deals.length) return true;
    var results = table.results || {};
    for (var i = 0; i < deals.length; i++) {
      var res = results[String(deals[i].id)] || {};
      var contract = (res.contract || '').toString().trim();
      var declarer = (res.declarer || '').toString().trim();
      var tricks = res.tricks_taken;
      if (contract === '' || declarer === '') return false;
      var t = Number(tricks);
      if (tricks == null || tricks === '' || isNaN(t) || t < 0 || t > 13) return false;
      if (res.ns_score == null && res.ew_score == null) return false;
    }
    return true;
  }

  /** True when save response said all results ok (round.all_deals_saved) or we have all data in memory (e.g. on load). */
  function roundAllDealsSaved(round) {
    if (!round) return false;
    if (round.all_deals_saved === true) return true;
    if (!round.tables || !round.tables.length) return false;
    var deals = round.deals || [];
    for (var i = 0; i < round.tables.length; i++) {
      if (!tableAllResultsFilledAndValidated(round.tables[i], deals)) return false;
    }
    return true;
  }

  function updateRoundPillStates() {
    if (!roundsData || !roundsList) return;
    var pills = roundsList.querySelectorAll('.round-pill');
    roundsData.rounds.forEach(function (rnd, i) {
      var pill = pills[i];
      if (pill) pill.classList.toggle('round-pill--complete', roundAllDealsSaved(rnd));
    });
  }

  /** Wyniki table: signed number or "—". */
  function formatScoreSigned(n) {
    if (n === null || n === undefined) return '—';
    var x = parseInt(n, 10);
    if (isNaN(x)) return '—';
    return x > 0 ? '+' + x : String(x);
  }

  /** Renders ranking table in #round-view-wyniki from API response. */
  function renderRankingInline(data) {
    if (!roundViewWyniki || !data) { roundViewWyniki.innerHTML = ''; lastRankingData = null; return; }
    if (data.error_message) {
      lastRankingData = null;
      roundViewWyniki.innerHTML = '<p class="errors" role="alert">' + escapeHtml(data.error_message) + '</p>' +
        '<p class="muted">Zapisz wszystkie rozdania w rundach 1–' + escapeHtml(String(data.round_number || '')) + ', aby zobaczyć ranking.</p>';
      return;
    }
    lastRankingData = data;
    var ranking = data.ranking || [];
    var roundNumbers = data.round_numbers || [];
    var html = '<table class="ranking-table"><thead><tr><th>Miejsce</th><th>Drużyna</th>';
    for (var rn = 0; rn < roundNumbers.length; rn++) {
      html += '<th>R' + roundNumbers[rn] + '</th>';
    }
    html += '<th class="ranking-total-col">Suma</th></tr></thead><tbody>';
    for (var i = 0; i < ranking.length; i++) {
      var r = ranking[i];
      var teamCell = '<span class="ranking-team-name">' + escapeHtml(r.team_name || '') + '</span>';
      var m1 = (r.member1 || '').trim();
      var m2 = (r.member2 || '').trim();
      if (m1 || m2) {
        teamCell += '<span class="ranking-team-players">' + escapeHtml([m1, m2].filter(Boolean).join(', ')) + '</span>';
      }
      html += '<tr><td>' + (i + 1) + '</td><td class="ranking-team-cell">' + teamCell + '</td>';
      var roundImps = r.round_imps || [];
      for (var ri = 0; ri < roundNumbers.length; ri++) {
        var imp = roundImps[ri];
        var val = imp != null ? (imp > 0 ? '+' + imp : String(imp)) : '—';
        html += '<td>' + escapeHtml(String(val)) + '</td>';
      }
      html += '<td class="ranking-total-cell">' + escapeHtml(formatScoreSigned(r.total_imp)) + '</td></tr>';
    }
    html += '</tbody></table>';
    roundViewWyniki.innerHTML = html;
  }

  function fetchAndRenderRanking() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !roundViewWyniki) return;
    var roundId = roundsData.rounds[selectedRoundIndex].round_id;
    lastRankingData = null;
    roundViewWyniki.innerHTML = '<p class="muted">Ładowanie rankingu…</p>';
    fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/rounds/' + encodeURIComponent(String(roundId)) + '/ranking')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        renderRankingInline(data || {});
      })
      .catch(function () {
        lastRankingData = null;
        roundViewWyniki.innerHTML = '<p class="errors">Błąd ładowania rankingu.</p>';
      });
  }

  function showOrHideRankingActions() {
    if (!roundViewRankingActions) return;
    var onRanking = roundViewMode === 'view' && viewTab === 'ranking';
    roundViewRankingActions.classList.toggle('hidden', !onRanking);
    roundViewRankingActions.setAttribute('aria-hidden', onRanking ? 'false' : 'true');
  }

  function rankingPrint() {
    var printExtra = document.getElementById('standings-print-extra');
    if (!roundsData || !roundsData.rounds[selectedRoundIndex]) {
      window.print();
      return;
    }
    var roundId = roundsData.rounds[selectedRoundIndex].round_id;
    var url = '/api/tournaments/' + encodeURIComponent(tourId) + '/rounds/' + encodeURIComponent(String(roundId)) + '/head-to-head';
    fetch(url)
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (printExtra) printExtra.innerHTML = buildHead2HeadHtml(data || {});
        var afterPrint = function () {
          if (printExtra) printExtra.innerHTML = '';
          window.removeEventListener('afterprint', afterPrint);
        };
        window.addEventListener('afterprint', afterPrint);
        window.print();
      })
      .catch(function () {
        if (printExtra) printExtra.innerHTML = '';
        window.print();
      });
  }

  /** Build CSV string from lastRankingData; fields escaped for CSV. */
  function buildRankingCsv() {
    if (!lastRankingData || !lastRankingData.ranking || !lastRankingData.ranking.length) return null;
    var ranking = lastRankingData.ranking;
    var roundNumbers = lastRankingData.round_numbers || [];
    function escapeCsv(val) {
      var s = String(val == null ? '' : val);
      if (s.indexOf('"') >= 0 || s.indexOf(',') >= 0 || s.indexOf('\n') >= 0 || s.indexOf('\r') >= 0) {
        return '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    }
    var headers = ['Miejsce', 'Drużyna'];
    for (var rn = 0; rn < roundNumbers.length; rn++) headers.push('R' + roundNumbers[rn]);
    headers.push('Suma');
    var rows = [headers.map(escapeCsv).join(',')];
    for (var i = 0; i < ranking.length; i++) {
      var r = ranking[i];
      var row = [i + 1, r.team_name || ''];
      var roundImps = r.round_imps || [];
      for (var ri = 0; ri < roundNumbers.length; ri++) {
        var imp = roundImps[ri];
        row.push(imp != null ? imp : '');
      }
      row.push(r.total_imp != null ? r.total_imp : '');
      rows.push(row.map(escapeCsv).join(','));
    }
    return rows.join('\r\n');
  }

  function rankingExportCsv() {
    var csv = buildRankingCsv();
    if (!csv) return;
    var roundNum = lastRankingData && lastRankingData.round_number != null ? lastRankingData.round_number : (roundsData && roundsData.rounds[selectedRoundIndex] ? roundsData.rounds[selectedRoundIndex].round_number : '');
    var filename = 'ranking-runda-' + roundNum + '.csv';
    var blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  /** Heatmap cell background from IMP value; maxAbs is max of |imp| for scale. */
  function head2headCellStyle(imp, maxAbs) {
    if (imp === 0 || maxAbs <= 0) return 'background: var(--h2h-bg-zero, #f1f5f9);';
    var intensity = Math.min(1, Math.abs(imp) / maxAbs);
    var r, g, b;
    if (imp < 0) {
      r = 255;
      g = Math.round(255 * (1 - intensity));
      b = Math.round(255 * (1 - intensity));
    } else {
      r = Math.round(255 * (1 - intensity));
      g = 255;
      b = Math.round(255 * (1 - intensity));
    }
    return 'background: rgb(' + r + ',' + g + ',' + b + ');';
  }

  function renderHead2HeadInline(data) {
    if (!roundViewWyniki || !data) { roundViewWyniki.innerHTML = ''; return; }
    if (data.error_message) {
      roundViewWyniki.innerHTML = '<p class="errors" role="alert">' + escapeHtml(data.error_message) + '</p>' +
        '<p class="muted">Zapisz wszystkie rozdania w rundach 1–' + escapeHtml(String(data.round_number || '')) + ', aby zobaczyć bezpośrednie starcia.</p>';
      return;
    }
    if (!(data.team_names || []).length) {
      roundViewWyniki.innerHTML = '<p class="muted">Brak danych bezpośrednich starć.</p>';
      return;
    }
    roundViewWyniki.innerHTML = buildHead2HeadHtml(data);
  }

  /** Build head-to-head HTML string (for inline view or print-extra). */
  function buildHead2HeadHtml(data) {
    if (!data || data.error_message) return '';
    var teamNames = data.team_names || [];
    var matrix = data.matrix || [];
    if (!teamNames.length) return '';
    var maxAbs = 0;
    for (var i = 0; i < matrix.length; i++) {
      for (var j = 0; j < (matrix[i] || []).length; j++) {
        if (i !== j) {
          var v = Math.abs(matrix[i][j]);
          if (v > maxAbs) maxAbs = v;
        }
      }
    }
    if (maxAbs < 1) maxAbs = 1;
    var html = '<div class="head2head-wrap"><p class="head2head-caption muted">IMP zdobyte przeciwko danej drużynie (rundy 1–' + escapeHtml(String(data.round_number || '')) + ')</p>';
    html += '<div class="head2head-scroll"><table class="head2head-table" role="grid">';
    html += '<thead><tr><th class="head2head-corner"></th>';
    for (var c = 0; c < teamNames.length; c++) {
      html += '<th class="head2head-col-header" scope="col" title="' + escapeHtml(teamNames[c]) + '">' + escapeHtml(teamNames[c]) + '</th>';
    }
    html += '</tr></thead><tbody>';
    for (var i = 0; i < teamNames.length; i++) {
      html += '<tr><th class="head2head-row-header" scope="row" title="' + escapeHtml(teamNames[i]) + '">' + escapeHtml(teamNames[i]) + '</th>';
      for (var j = 0; j < teamNames.length; j++) {
        var imp = (matrix[i] && matrix[i][j] != null) ? matrix[i][j] : null;
        var cellClass = 'head2head-cell';
        if (i === j) cellClass += ' head2head-cell--diag';
        var style = i === j ? '' : (imp != null ? head2headCellStyle(imp, maxAbs) : '');
        var text = i === j ? '—' : (imp != null ? (imp > 0 ? '+' + imp : String(imp)) : '—');
        html += '<td class="' + cellClass + '" style="' + style + '" data-imp="' + (imp != null ? imp : '') + '">' + escapeHtml(text) + '</td>';
      }
      html += '</tr>';
    }
    html += '</tbody></table></div>';
    html += '<div class="head2head-legend"><span class="head2head-legend-item head2head-legend--neg">← strata IMP</span><span class="head2head-legend-item head2head-legend--zero">0</span><span class="head2head-legend-item head2head-legend--pos">zysk IMP →</span></div></div>';
    return html;
  }

  function fetchAndRenderHead2Head() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !roundViewWyniki) return;
    var roundId = roundsData.rounds[selectedRoundIndex].round_id;
    roundViewWyniki.innerHTML = '<p class="muted">Ładowanie starć bezpośrednich…</p>';
    fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/rounds/' + encodeURIComponent(String(roundId)) + '/head-to-head')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        renderHead2HeadInline(data || {});
      })
      .catch(function () {
        roundViewWyniki.innerHTML = '<p class="errors">Błąd ładowania starć bezpośrednich.</p>';
      });
  }

  /** Builds deal-results-section + table per deal from API response. */
  function renderWynikiInline(data) {
    if (!roundViewWyniki || !data || !data.deals_with_tables) { roundViewWyniki.innerHTML = ''; return; }
    var html = '';
    var vul = data.deals_with_tables;
    for (var i = 0; i < vul.length; i++) {
      var item = vul[i];
      var deal = item.deal || {};
      html += '<div class="deal-results-section">';
      html += '<div class="deal-results-header">';
      html += '<span class="deal-board">Rozdanie ' + escapeHtml(String(deal.number)) + '</span>';
      html += buildBoxInfoHtml(deal.box, deal.dealer, deal.vulnerability);
      html += '</div>';
      html += '<div class="deal-results-table-wrap"><table class="deal-results-table">';
      html += '<thead><tr><th>Stół</th><th>NS</th><th>EW</th><th>Kontrakt</th><th>Rozgrywał</th><th>Wist</th><th>Wziątki</th><th>Pkt NS</th><th>Pkt EW</th><th>IMP NS</th><th>IMP EW</th></tr></thead><tbody>';
      var rows = item.table_rows || [];
      for (var j = 0; j < rows.length; j++) {
        var row = rows[j];
        html += '<tr><td>' + escapeHtml(String(row.table_number)) + '</td><td>' + escapeHtml(row.ns_team || '') + '</td><td>' + escapeHtml(row.ew_team || '') + '</td>';
        html += '<td>' + escapeHtml(row.contract || '—') + '</td><td>' + escapeHtml(row.declarer || '—') + '</td><td>' + escapeHtml(String(row.opening_lead || '—')) + '</td><td>' + escapeHtml(String(row.tricks_taken !== undefined && row.tricks_taken !== null ? row.tricks_taken : '—')) + '</td>';
        html += '<td>' + formatScoreSigned(row.ns_score) + '</td><td>' + formatScoreSigned(row.ew_score) + '</td>';
        html += '<td class="deal-imp-cell">' + formatScoreSigned(row.ns_imp) + '</td><td class="deal-imp-cell">' + formatScoreSigned(row.ew_imp) + '</td></tr>';
      }
      html += '</tbody></table></div></div>';
    }
    roundViewWyniki.innerHTML = html;
  }

  function fetchAndRenderWyniki() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !roundViewWyniki) return;
    var roundId = roundsData.rounds[selectedRoundIndex].round_id;
    roundViewWyniki.innerHTML = '<p class="muted">Ładowanie wyników…</p>';
    fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/rounds/' + encodeURIComponent(String(roundId)) + '/deal-results')
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        renderWynikiInline(data || {});
      })
      .catch(function () {
        roundViewWyniki.innerHTML = '<p class="errors">Błąd ładowania wyników.</p>';
      });
  }

  function getViewParam() {
    if (roundViewMode === 'edit') return 'edit';
    if (viewTab === 'ranking') return 'standings';
    if (viewTab === 'head2head') return 'head2head';
    return 'results';
  }

  function updateRoundUrl() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !window.history.replaceState) return;
    var rnd = roundsData.rounds[selectedRoundIndex];
    var view = getViewParam();
    var newUrl = window.location.pathname + '?round=' + encodeURIComponent(String(rnd.round_id)) + '&view=' + encodeURIComponent(view);
    window.history.replaceState({ round: rnd.round_id, view: view }, '', newUrl);
  }

  function setRoundPanel(mode) {
    var isEdit = mode === 'edit';
    if (roundDetailEdit) roundDetailEdit.classList.toggle('hidden', !isEdit);
    if (roundDetailView) roundDetailView.classList.toggle('hidden', isEdit);
    if (roundDetailEditActions) roundDetailEditActions.classList.toggle('hidden', !isEdit);
    if (roundDetailViewActions) roundDetailViewActions.classList.toggle('hidden', isEdit);
    if (!isEdit) {
      // Keep current view tab and refresh content for selected round
      if (tabWyniki && tabRanking && tabHead2Head) {
        tabWyniki.classList.toggle('active', viewTab === 'wyniki');
        tabWyniki.setAttribute('aria-selected', viewTab === 'wyniki');
        tabRanking.classList.toggle('active', viewTab === 'ranking');
        tabRanking.setAttribute('aria-selected', viewTab === 'ranking');
        tabHead2Head.classList.toggle('active', viewTab === 'head2head');
        tabHead2Head.setAttribute('aria-selected', viewTab === 'head2head');
      }
      showOrHideRankingActions();
      if (viewTab === 'wyniki') fetchAndRenderWyniki();
      else if (viewTab === 'ranking') fetchAndRenderRanking();
      else if (viewTab === 'head2head') fetchAndRenderHead2Head();
    }
  }

  function switchViewTab(view) {
    if (!tabWyniki || !tabRanking || !tabHead2Head) return;
    viewTab = view === 'ranking' ? 'ranking' : view === 'head2head' ? 'head2head' : 'wyniki';
    tabWyniki.classList.toggle('active', viewTab === 'wyniki');
    tabWyniki.setAttribute('aria-selected', viewTab === 'wyniki');
    tabRanking.classList.toggle('active', viewTab === 'ranking');
    tabRanking.setAttribute('aria-selected', viewTab === 'ranking');
    tabHead2Head.classList.toggle('active', viewTab === 'head2head');
    tabHead2Head.setAttribute('aria-selected', viewTab === 'head2head');
    showOrHideRankingActions();
    if (viewTab === 'wyniki') fetchAndRenderWyniki();
    else if (viewTab === 'ranking') fetchAndRenderRanking();
    else if (viewTab === 'head2head') fetchAndRenderHead2Head();
    updateRoundUrl();
  }

  function updateTableCardCheckmarks() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !tablesList) return;
    var rnd = roundsData.rounds[selectedRoundIndex];
    var deals = rnd.deals || [];
    var cards = tablesList.querySelectorAll('.table-card-with-deals');
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var tableNum = parseInt(card.getAttribute('data-table-number'), 10);
      var t = rnd.tables.find(function (x) { return x.table_number === tableNum; });
      var allFilledAndValidated = t ? tableAllResultsFilledAndValidated(t, deals) : false;
      card.classList.toggle('table-card-check-ok', allFilledAndValidated);
    }
  }

  function getRowFocusables(rowEl) {
    if (!rowEl) return [];
    var c = rowEl.querySelector('.deal-contract');
    var d = rowEl.querySelector('.deal-declarer');
    var l = rowEl.querySelector('.deal-lead');
    var t = rowEl.querySelector('.deal-tricks');
    return [c, d, l, t].filter(Boolean);
  }

  /** Move focus to next or previous input in the deal table (same row or adjacent row, expanding card if needed). */
  function focusAdjacentRowInput(row, direction) {
    if (!tablesList || !row) return;
    var allRows = Array.prototype.slice.call(tablesList.querySelectorAll('.deal-row'));
    var rowIdx = allRows.indexOf(row);
    var focusables = getRowFocusables(row);
    var idx = focusables.indexOf(document.activeElement);
    if (direction === 'prev') {
      if (idx > 0) {
        focusables[idx - 1].focus();
        return;
      }
      if (rowIdx > 0) {
        var prevRow = allRows[rowIdx - 1];
        var prevCard = prevRow.closest('.table-card-with-deals');
        if (prevCard && prevCard.classList.contains('collapsed')) prevCard.querySelector('.table-card').click();
        var lastInput = getRowFocusables(prevRow)[3];
        if (lastInput) setTimeout(function () { lastInput.focus(); }, 0);
      }
    } else {
      if (idx >= 0 && idx < 3) {
        focusables[idx + 1].focus();
        return;
      }
      if (rowIdx >= 0 && rowIdx < allRows.length - 1) {
        var nextRow = allRows[rowIdx + 1];
        var nextCard = nextRow.closest('.table-card-with-deals');
        if (nextCard && nextCard.classList.contains('collapsed')) nextCard.querySelector('.table-card').click();
        var firstInput = getRowFocusables(nextRow)[0];
        if (firstInput) setTimeout(function () { firstInput.focus(); }, 0);
      }
    }
  }

  /** Ask backend to validate row on blur; updates row state and score from response. */
  function validateDealRowOnBlur(rowEl) {
    if (!rowEl) return;
    var contractIn = rowEl.querySelector('.deal-contract');
    var declarerIn = rowEl.querySelector('.deal-declarer');
    var leadIn = rowEl.querySelector('.deal-lead');
    var tricksIn = rowEl.querySelector('.deal-tricks');
    var contract = contractIn ? contractIn.value.trim() : '';
    var declarer = declarerIn ? declarerIn.value.trim() : '';
    var lead = leadIn ? leadIn.value.trim() : '';
    var tricksRaw = tricksIn ? tricksIn.value.trim() : '';
    var vulnerability = (rowEl.getAttribute('data-vulnerability') || 'None').trim() || 'None';
    var filled = contract !== '' || declarer !== '' || lead !== '' || tricksRaw !== '';
    if (!filled) {
      setDealRowStateFromValidation(rowEl, 'empty', []);
      return;
    }
    var payload = { contract: contract, declarer: declarer, opening_lead: normalizeOpeningLead(lead), tricks_taken: tricksRaw === '' ? null : tricksRaw, vulnerability: vulnerability };
    fetch('/api/validate-result', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.valid) {
          setDealRowStateFromValidation(rowEl, true, []);
          var scoreEl = rowEl.querySelector('.deal-score');
          var decl = rowEl.querySelector('.deal-declarer');
          if (scoreEl) scoreEl.textContent = formatScore(data.ns_score, data.ew_score, decl ? decl.value : '');
          var tableNum = parseInt(rowEl.getAttribute('data-table-number'), 10);
          var dealId = rowEl.getAttribute('data-deal-id');
          if (roundsData && roundsData.rounds[selectedRoundIndex] && dealId) {
            var t = roundsData.rounds[selectedRoundIndex].tables.find(function (x) { return x.table_number === tableNum; });
            if (t && t.results) {
              var tricksVal = tricksRaw === '' ? null : parseInt(tricksRaw, 10);
              if (tricksVal !== null && isNaN(tricksVal)) tricksVal = null;
              t.results[dealId] = { contract: contract, declarer: declarer, opening_lead: normalizeOpeningLead(lead), tricks_taken: tricksVal, ns_score: data.ns_score != null ? data.ns_score : 0, ew_score: data.ew_score != null ? data.ew_score : 0 };
              updateTableCardCheckmarks();
            }
          }
        } else {
          setDealRowStateFromValidation(rowEl, false, data.errors || []);
        }
      })
      .catch(function () {
        setDealRowStateFromValidation(rowEl, false, [{ field: '_', message: 'Błąd walidacji.' }]);
      });
  }

  /** Row state from stored result: true = backend-validated (has scores), 'empty', or null (incomplete / not yet validated). */
  function rowStateFromStoredResult(res) {
    if (!res) return 'empty';
    var contract = (res.contract || '').toString().trim();
    var declarer = (res.declarer || '').toString().trim();
    var lead = (res.opening_lead || '').toString().trim();
    var tricks = res.tricks_taken;
    var hasScores = res.ns_score != null || res.ew_score != null;
    if (contract === '' && declarer === '' && lead === '' && (tricks == null || tricks === '')) return 'empty';
    var t = Number(tricks);
    if (contract !== '' && declarer !== '' && !isNaN(t) && t >= 0 && t <= 13 && hasScores) return true;
    return null;
  }

  function saveRoundResults() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !btnSaveRound) return;
    var roundId = roundsData.rounds[selectedRoundIndex].round_id;
    var rows = tablesList.querySelectorAll('.deal-row');
    var resultsPayload = [];
    var rowMap = [];
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var tableNumber = parseInt(row.getAttribute('data-table-number'), 10);
      var dealId = parseInt(row.getAttribute('data-deal-id'), 10);
      var contractIn = row.querySelector('.deal-contract');
      var declarerIn = row.querySelector('.deal-declarer');
      var leadIn = row.querySelector('.deal-lead');
      var tricksIn = row.querySelector('.deal-tricks');
      var contract = contractIn ? contractIn.value.trim() : '';
      var declarer = declarerIn ? declarerIn.value.trim() : '';
      var lead = leadIn ? leadIn.value.trim() : '';
      var tricksRaw = tricksIn ? tricksIn.value.trim() : '';
      var tricks = tricksRaw === '' ? null : parseInt(tricksRaw, 10);
      if (tricks !== null && isNaN(tricks)) tricks = null;
      resultsPayload.push({
        table_number: tableNumber,
        deal_id: dealId,
        contract: contract,
        declarer: declarer,
        opening_lead: normalizeOpeningLead(lead),
        tricks_taken: tricks
      });
      rowMap.push({ row: row, contractEl: row.querySelector('.deal-contract-error'), declarerEl: row.querySelector('.deal-declarer-error'), leadEl: row.querySelector('.deal-lead-error'), tricksEl: row.querySelector('.deal-tricks-error') });
    }
    btnSaveRound.disabled = true;
    btnSaveRound.textContent = '…';
    if (saveRoundStatus) { saveRoundStatus.textContent = ''; saveRoundStatus.className = 'save-round-status'; }
    var payload = { round_id: roundId, results: resultsPayload };
    fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/round-results', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return (res.json && res.json()).then(function (data) {
          return { res: res, data: data || {} };
        }).catch(function () { return { res: res, data: {} }; });
      })
      .then(function (result) {
        var res = result.res;
        var data = result.data;
        var total = rowMap.length;
        if (!res.ok || !data.results || !Array.isArray(data.results)) {
          if (saveRoundStatus) {
            saveRoundStatus.textContent = 'Błąd zapisu.';
            saveRoundStatus.className = 'save-round-status save-round-status--error';
          }
          return;
        }
        var saved = data.saved != null ? data.saved : 0;
        data.results.forEach(function (r, idx) {
          var entry = rowMap[idx];
          if (!entry) return;
          if (entry.contractEl) { entry.contractEl.textContent = ''; entry.contractEl.classList.add('hidden'); }
          if (entry.declarerEl) { entry.declarerEl.textContent = ''; entry.declarerEl.classList.add('hidden'); }
          if (entry.leadEl) { entry.leadEl.textContent = ''; entry.leadEl.classList.add('hidden'); }
          if (entry.tricksEl) { entry.tricksEl.textContent = ''; entry.tricksEl.classList.add('hidden'); }
          if (r && r.ok) {
            setDealRowStateFromValidation(entry.row, true, []);
            var scoreEl = entry.row.querySelector('.deal-score');
            var declSelect = entry.row.querySelector('.deal-declarer');
            if (scoreEl && (r.ns_score != null || r.ew_score != null)) scoreEl.textContent = formatScore(r.ns_score, r.ew_score, declSelect ? declSelect.value : '');
          } else if (r && r.ok === false) {
            var msg = (r.error || 'Błąd').toString();
            var field = r.field || 'contract';
            var errEl = field === 'contract' ? entry.contractEl : field === 'declarer' ? entry.declarerEl : field === 'opening_lead' ? entry.leadEl : field === 'tricks_taken' ? entry.tricksEl : entry.contractEl;
            if (errEl) { errEl.textContent = msg; errEl.classList.remove('hidden'); }
            setDealRowStateFromValidation(entry.row, false, [{ field: field, message: msg }]);
          } else {
            setDealRowStateFromValidation(entry.row, null, []);
          }
        });
        var allSavedByBackend = data.results.length > 0 && data.results.every(function (r) { return r && r.ok === true; });
        if (roundsData && roundsData.rounds[selectedRoundIndex]) {
          var rnd = roundsData.rounds[selectedRoundIndex];
          for (var j = 0; j < resultsPayload.length && j < data.results.length; j++) {
            var r = data.results[j];
            if (!r || !r.ok) continue;
            var payloadItem = resultsPayload[j];
            var t = rnd.tables.find(function (x) { return x.table_number === payloadItem.table_number; });
            if (t && t.results) {
              t.results[String(payloadItem.deal_id)] = {
                contract: payloadItem.contract,
                declarer: payloadItem.declarer,
                opening_lead: payloadItem.opening_lead,
                tricks_taken: payloadItem.tricks_taken,
                ns_score: r.ns_score != null ? r.ns_score : 0,
                ew_score: r.ew_score != null ? r.ew_score : 0
              };
            }
          }
          if (allSavedByBackend) rnd.all_deals_saved = true;
        }
        roundsHasUnsavedChanges = false;
        updateTableCardCheckmarks();
        updateRoundPillStates();
        if (allSavedByBackend) {
          roundViewMode = 'view';
          setRoundPanel('view');
        }
        if (saveRoundStatus) {
          var savedCount = 0;
          for (var k = 0; k < data.results.length; k++) { if (data.results[k] && data.results[k].ok) savedCount++; }
          var totalCount = data.results.length;
          var errorCount = totalCount - savedCount;
          if (savedCount === totalCount && savedCount > 0) {
            saveRoundStatus.textContent = 'Zapisano ' + savedCount + ' z ' + totalCount + ' wyników.';
            saveRoundStatus.className = 'save-round-status save-round-status--success';
          } else if (savedCount > 0) {
            var errWord = errorCount === 1 ? '1 wiersz zawiera' : (errorCount < 5 ? errorCount + ' wiersze zawierają' : errorCount + ' wierszy zawierają');
            saveRoundStatus.textContent = 'Zapisano ' + savedCount + ' z ' + totalCount + ' wyników. ' + errWord + ' błędy – popraw je i zapisz ponownie.';
            saveRoundStatus.className = 'save-round-status save-round-status--partial';
          } else {
            saveRoundStatus.textContent = 'Żaden wynik nie został zapisany. Wszystkie wiersze zawierają błędy – popraw je i zapisz ponownie.';
            saveRoundStatus.className = 'save-round-status save-round-status--partial';
          }
        }
      })
      .catch(function () {
        if (saveRoundStatus) {
          saveRoundStatus.textContent = 'Błąd zapisu.';
          saveRoundStatus.className = 'save-round-status save-round-status--error';
        }
      })
      .then(function () {
        btnSaveRound.disabled = false;
        btnSaveRound.textContent = 'Zapisz rundę';
      });
  }

  function setAutoButtonVisibility(debugMode) {
    if (btnAutoRound) btnAutoRound.style.display = debugMode ? '' : 'none';
  }
  setAutoButtonVisibility(false);
  if (window.BridgeSettings) {
    window.BridgeSettings.ready()
      .then(function (data) { setAutoButtonVisibility(!!data.debug_mode); })
      .catch(function () { setAutoButtonVisibility(false); });
    window.BridgeSettings.subscribe(function (settings) {
      setAutoButtonVisibility(!!settings.debug_mode);
    });
  }

  function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function fillRoundWithRandomContracts() {
    if (!tablesList) return;
    var rows = tablesList.querySelectorAll('.deal-row');
    var levels = [1, 2, 3, 4, 5, 6, 7];
    var suits = ['C', 'D', 'H', 'S', 'NT'];
    var modifiers = ['', 'x', 'xx'];
    var declarers = ['N', 'S', 'E', 'W'];
    var leadRanks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
    var leadSuits = ['C', 'D', 'H', 'S'];
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var contract = randomChoice(levels) + '' + randomChoice(suits) + randomChoice(modifiers);
      var declarer = randomChoice(declarers);
      var lead = randomChoice(leadRanks) + randomChoice(leadSuits);
      var tricks = Math.floor(Math.random() * 14);
      var contractIn = row.querySelector('.deal-contract');
      var declarerIn = row.querySelector('.deal-declarer');
      var leadIn = row.querySelector('.deal-lead');
      var tricksIn = row.querySelector('.deal-tricks');
      if (contractIn) contractIn.value = contract;
      if (declarerIn) declarerIn.value = declarer;
      if (leadIn) leadIn.value = lead;
      if (tricksIn) tricksIn.value = tricks;
      roundsHasUnsavedChanges = true;
      validateDealRowOnBlur(row);
    }
    updateTableCardCheckmarks();
  }

  if (btnAutoRound) {
    btnAutoRound.addEventListener('click', function () {
      fillRoundWithRandomContracts();
    });
  }

  function buildTablesList() {
    if (!roundsData || !roundsData.rounds[selectedRoundIndex] || !tablesList) return;
    var rnd = roundsData.rounds[selectedRoundIndex];
    var deals = rnd.deals || [];
    tablesList.innerHTML = '';
    rnd.tables.forEach(function (t) {
      const card = document.createElement('div');
      card.className = 'table-card-with-deals collapsed';
      card.setAttribute('data-table-number', String(t.table_number));
      const results = t.results || {};
      var allFilledAndValidated = tableAllResultsFilledAndValidated(t, deals);
      if (allFilledAndValidated) card.classList.add('table-card-check-ok');
      card.innerHTML =
        '<div class="table-card" role="button" tabindex="0" aria-expanded="false" aria-label="Pokaż rozdania">' +
          '<div class="table-card-header">' +
            '<span class="table-card-title">Stół ' + escapeHtml(String(t.table_number)) + '</span>' +
            '<span class="table-card-teams">NS: ' + escapeHtml(t.ns_team.name) + ', EW: ' + escapeHtml(t.ew_team.name) + '</span>' +
            '<span class="table-card-check" aria-hidden="true">✓</span>' +
            '<span class="table-card-chevron" aria-hidden="true">▸</span>' +
          '</div>' +
        '</div>' +
        '<div class="table-deals" hidden></div>';
      const tableCard = card.querySelector('.table-card');
      const dealsContainer = card.querySelector('.table-deals');
      function toggleDeals() {
        card.classList.toggle('collapsed');
        var isCollapsed = card.classList.contains('collapsed');
        dealsContainer.hidden = isCollapsed;
        tableCard.setAttribute('aria-expanded', !isCollapsed);
        tableCard.setAttribute('aria-label', isCollapsed ? 'Pokaż rozdania' : 'Ukryj rozdania');
      }
      tableCard.addEventListener('click', toggleDeals);
      tableCard.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleDeals(); }
      });
      if (deals.length > 0) {
        const dealsTitle = document.createElement('div');
        dealsTitle.className = 'table-deals-title';
        dealsTitle.textContent = 'Rozdania';
        dealsContainer.appendChild(dealsTitle);
      }
      var DECLARERS = ['N', 'S', 'E', 'W'];
      deals.forEach(function (d) {
        const res = results[String(d.id)] || {};
        const row = document.createElement('div');
        row.className = 'deal-row';
        row.setAttribute('data-table-number', String(t.table_number));
        row.setAttribute('data-deal-id', String(d.id));
        row.setAttribute('data-vulnerability', d.vulnerability || 'None');
        var declarerVal = (res.declarer || '').toUpperCase();
        if (DECLARERS.indexOf(declarerVal) === -1) declarerVal = '';
        var scoreText = formatScore(res.ns_score, res.ew_score, declarerVal);
        row.innerHTML =
          '<div class="deal-info">' +
            buildBoxInfoHtml(d.box, d.dealer, d.vulnerability) +
          '</div>' +
          '<div class="deal-field"><label><span>Kontrakt</span><input type="text" class="deal-input deal-contract" placeholder="3NT" value="' + escapeHtml(res.contract || '') + '"></label><span class="deal-contract-error hidden" aria-live="polite"></span></div>' +
          '<div class="deal-field"><label><span>Rozgrywał</span><select class="deal-input deal-declarer"><option value="">—</option><option value="N"' + (declarerVal === 'N' ? ' selected' : '') + '>N</option><option value="S"' + (declarerVal === 'S' ? ' selected' : '') + '>S</option><option value="E"' + (declarerVal === 'E' ? ' selected' : '') + '>E</option><option value="W"' + (declarerVal === 'W' ? ' selected' : '') + '>W</option></select></label><span class="deal-declarer-error hidden" aria-live="polite"></span></div>' +
          '<div class="deal-field"><label><span>Wist</span><input type="text" class="deal-input deal-lead" placeholder="A♠" value="' + escapeHtml(res.opening_lead || '') + '"></label><span class="deal-lead-error hidden" aria-live="polite"></span></div>' +
          '<div class="deal-field"><label><span>Wziątki</span><input type="number" class="deal-input deal-tricks" min="0" max="13" placeholder="—" value="' + (res.tricks_taken != null ? escapeHtml(String(res.tricks_taken)) : '') + '"></label><span class="deal-tricks-error hidden" aria-live="polite"></span></div>' +
          '<div class="deal-field deal-score-wrap"><span class="deal-score">' + escapeHtml(scoreText) + '</span></div>';
        var initialValid = rowStateFromStoredResult(res);
        setDealRowStateFromValidation(row, initialValid, []);
        row.addEventListener('focusout', function (e) {
          setTimeout(function () {
            if (!row.contains(document.activeElement)) {
              validateDealRowOnBlur(row);
            }
          }, 0);
        });
        dealsContainer.appendChild(row);
      });
      tablesList.appendChild(card);
    });
    if (btnSaveRound) btnSaveRound.onclick = saveRoundResults;
  }

  function switchToEditMode() {
    roundViewMode = 'edit';
    if (saveRoundStatus) { saveRoundStatus.textContent = ''; saveRoundStatus.className = 'save-round-status'; }
    buildTablesList();
    setRoundPanel('edit');
    updateRoundUrl();
  }

  function setRound(index) {
    if (!roundsData || !roundsData.rounds.length) return;
    selectedRoundIndex = Math.max(0, Math.min(index, roundsData.rounds.length - 1));
    const rnd = roundsData.rounds[selectedRoundIndex];
    roundDetailTitle.textContent = 'Runda ' + rnd.round_number;
    if (roundDetailCaption) roundDetailCaption.textContent = roundsData.rounds.length ? ' z ' + roundsData.rounds.length : '';
    document.querySelectorAll('.round-pill').forEach(function (el, i) {
      el.classList.toggle('selected', i === selectedRoundIndex);
    });
    roundViewMode = roundAllDealsSaved(rnd) ? 'view' : 'edit';
    if (roundViewMode === 'edit') {
      if (saveRoundStatus) { saveRoundStatus.textContent = ''; saveRoundStatus.className = 'save-round-status'; }
      buildTablesList();
      setRoundPanel('edit');
    } else {
      setRoundPanel('view');
    }
    updateRoundUrl();
  }

  if (tabWyniki) tabWyniki.addEventListener('click', function () { switchViewTab('wyniki'); });
  if (tabRanking) tabRanking.addEventListener('click', function () { switchViewTab('ranking'); });
  if (tabHead2Head) tabHead2Head.addEventListener('click', function () { switchViewTab('head2head'); });
  if (btnRankingPrint) btnRankingPrint.addEventListener('click', rankingPrint);
  if (btnRankingExport) btnRankingExport.addEventListener('click', rankingExportCsv);

  function renderRoundsList() {
    if (!roundsData || !roundsList) return;
    roundsList.innerHTML = '';
    if (!roundsData.rounds.length) return;
    roundsData.rounds.forEach(function (rnd, i) {
      const pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'round-pill' + (i === selectedRoundIndex ? ' selected' : '') + (roundAllDealsSaved(rnd) ? ' round-pill--complete' : '');
      pill.textContent = 'Runda ' + rnd.round_number;
      pill.addEventListener('click', function () {
        setRound(i);
      });
      roundsList.appendChild(pill);
    });
  }

  linkEdit.href = '/tournament/' + encodeURIComponent(tourId);

  if (btnRoundEdit) {
    btnRoundEdit.addEventListener('click', function () { switchToEditMode(); });
  }

  tablesList.addEventListener('input', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('deal-input')) roundsHasUnsavedChanges = true;
  });
  tablesList.addEventListener('change', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('deal-input')) roundsHasUnsavedChanges = true;
  });

  window.addEventListener('beforeunload', function (e) {
    if (roundsHasUnsavedChanges) { e.preventDefault(); e.returnValue = ''; }
  });

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a || !roundsHasUnsavedChanges) return;
    var href = (a.getAttribute('href') || '').trim();
    if (!href || href === '#' || href.indexOf('#') === 0) return;
    e.preventDefault();
    if (confirm('Masz niezapisane zmiany. Czy na pewno chcesz opuścić stronę?')) {
      window.location.href = a.href;
    }
  });

  tablesList.addEventListener('keydown', function (e) {
    if (!tablesList.contains(e.target)) return;
    var row = e.target.closest('.deal-row');
    if (!row) return;
    if (!e.target.closest('.deal-input') || !row.contains(e.target)) return;
    if (e.key === 'Tab') {
      e.preventDefault();
      focusAdjacentRowInput(row, e.shiftKey ? 'prev' : 'next');
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      focusAdjacentRowInput(row, 'next');
    }
  });

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      if (roundViewMode === 'edit' && btnSaveRound && !btnSaveRound.disabled) {
        e.preventDefault();
        saveRoundResults();
      }
    }
  });

  fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/rounds')
    .then(function (res) {
      if (!res.ok) {
        if (res.status === 404) {
          loadError.textContent = 'Turniej nie znaleziony.';
        } else {
          loadError.textContent = 'Błąd ładowania rund.';
        }
        loadError.classList.remove('hidden');
        return null;
      }
      return res.json();
    })
    .then(function (data) {
      if (!data) return;
      roundsData = data;
      var tourName = data.name || 'Rundy';
      tournamentTitle.textContent = tourName;
      var breadcrumbName = document.getElementById('breadcrumb-tournament-name');
      if (breadcrumbName) breadcrumbName.textContent = tourName;
      roundsMeta.textContent = 'Data: ' + (data.date || '');
      renderRoundsList();
      var initialIndex = 0;
      var roundParam = (function () {
        var m = window.location.search.match(/[?&]round=(\d+)/);
        return m ? parseInt(m[1], 10) : null;
      })();
      if (roundParam != null && data.rounds && data.rounds.length) {
        var idx = data.rounds.findIndex(function (r) { return r.round_id === roundParam; });
        if (idx >= 0) initialIndex = idx;
      } else if (data.rounds && data.rounds.length) {
        var firstIncomplete = data.rounds.findIndex(function (r) { return !roundAllDealsSaved(r); });
        if (firstIncomplete >= 0) initialIndex = firstIncomplete;
        else initialIndex = data.rounds.length - 1;
      }
      var viewParam = (function () {
        var m = window.location.search.match(/[?&]view=(edit|results|standings|head2head)/);
        return m ? m[1] : null;
      })();
      setRound(initialIndex);
      if (viewParam === 'standings' && roundViewMode === 'view') switchViewTab('ranking');
      else if (viewParam === 'head2head' && roundViewMode === 'view') switchViewTab('head2head');
      else if ((viewParam === 'results' || viewParam === 'standings') && roundViewMode === 'edit') updateRoundUrl();
      roundsContent.classList.remove('hidden');
    });
})();
