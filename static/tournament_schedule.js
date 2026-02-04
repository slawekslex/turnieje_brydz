(function () {
  const tourId = window.TOUR_ID;
  const scheduleContent = document.getElementById('schedule-content');
  const loadError = document.getElementById('load-error');
  const tournamentTitle = document.getElementById('tournament-title');
  const scheduleMeta = document.getElementById('schedule-meta');
  const roundsList = document.getElementById('rounds-list');
  const roundDetailTitle = document.getElementById('round-detail-title');
  const roundDetailCaption = document.getElementById('round-detail-caption');
  const tablesList = document.getElementById('tables-list');
  const linkEdit = document.getElementById('link-edit');
  const btnSaveRound = document.getElementById('btn-save-round');
  const saveRoundStatus = document.getElementById('save-round-status');

  let schedule = null;
  let selectedRoundIndex = 0;
  let scheduleHasUnsavedChanges = false;

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
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
      var lead = (res.opening_lead || '').toString().trim();
      var tricks = res.tricks_taken;
      if (contract === '' || declarer === '' || lead === '') return false;
      var t = Number(tricks);
      if (tricks == null || tricks === '' || isNaN(t) || t < 0 || t > 13) return false;
      if (res.ns_score == null && res.ew_score == null) return false;
    }
    return true;
  }

  function updateTableCardCheckmarks() {
    if (!schedule || !schedule.rounds[selectedRoundIndex] || !tablesList) return;
    var rnd = schedule.rounds[selectedRoundIndex];
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
    var payload = { contract: contract, declarer: declarer, opening_lead: lead, tricks_taken: tricksRaw === '' ? null : tricksRaw, vulnerability: vulnerability };
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
          if (schedule && schedule.rounds[selectedRoundIndex] && dealId) {
            var t = schedule.rounds[selectedRoundIndex].tables.find(function (x) { return x.table_number === tableNum; });
            if (t && t.results) {
              var tricksVal = tricksRaw === '' ? null : parseInt(tricksRaw, 10);
              if (tricksVal !== null && isNaN(tricksVal)) tricksVal = null;
              t.results[dealId] = { contract: contract, declarer: declarer, opening_lead: lead, tricks_taken: tricksVal, ns_score: data.ns_score != null ? data.ns_score : 0, ew_score: data.ew_score != null ? data.ew_score : 0 };
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
    if (contract !== '' && declarer !== '' && lead !== '' && !isNaN(t) && t >= 0 && t <= 13 && hasScores) return true;
    return null;
  }

  function saveRoundResults() {
    if (!schedule || !schedule.rounds[selectedRoundIndex] || !btnSaveRound) return;
    var roundId = schedule.rounds[selectedRoundIndex].round_id;
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
        opening_lead: lead,
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
        if (schedule && schedule.rounds[selectedRoundIndex]) {
          for (var j = 0; j < resultsPayload.length && j < data.results.length; j++) {
            var r = data.results[j];
            if (!r || !r.ok) continue;
            var payloadItem = resultsPayload[j];
            var t = schedule.rounds[selectedRoundIndex].tables.find(function (x) { return x.table_number === payloadItem.table_number; });
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
        }
        scheduleHasUnsavedChanges = false;
        updateTableCardCheckmarks();
        if (saveRoundStatus) {
          var savedCount = 0;
          for (var k = 0; k < data.results.length; k++) { if (data.results[k] && data.results[k].ok) savedCount++; }
          var totalCount = data.results.length;
          if (savedCount === totalCount && savedCount > 0) {
            saveRoundStatus.textContent = 'Wszystkie rozdania zapisane.';
            saveRoundStatus.className = 'save-round-status save-round-status--success';
          } else if (savedCount > 0) {
            saveRoundStatus.textContent = 'Zapisano ' + savedCount + '/' + totalCount + ' rozdań.';
            saveRoundStatus.className = 'save-round-status save-round-status--partial';
          } else {
            saveRoundStatus.textContent = 'Błędy w danych – popraw oznaczone pola.';
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

  function setRound(index) {
    if (!schedule || !schedule.rounds.length) return;
    selectedRoundIndex = Math.max(0, Math.min(index, schedule.rounds.length - 1));
    const rnd = schedule.rounds[selectedRoundIndex];
    roundDetailTitle.textContent = 'Runda ' + rnd.round_number;
    if (roundDetailCaption) roundDetailCaption.textContent = schedule.rounds.length ? ' z ' + schedule.rounds.length : '';
    if (saveRoundStatus) { saveRoundStatus.textContent = ''; saveRoundStatus.className = 'save-round-status'; }
    tablesList.innerHTML = '';
    const deals = rnd.deals || [];
    if (deals.length > 0) {
      var topHeader = document.createElement('div');
      topHeader.className = 'deal-row-header deal-row-header--global';
      topHeader.innerHTML = '<span class="deal-header-cell deal-header-board">Board</span><span class="deal-header-cell">Kontrakt</span><span class="deal-header-cell">Rozgrywał</span><span class="deal-header-cell">Wist</span><span class="deal-header-cell">Wziątki</span><span class="deal-header-cell">Pkt</span>';
      tablesList.appendChild(topHeader);
    }
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
        var vul = (d.vulnerability || 'None').trim();
        var nsVul = vul === 'N-S' || vul === 'Both';
        var ewVul = vul === 'E-W' || vul === 'Both';
        var vulLabel = '<span class="vul-label">' +
          '<span class="vul-seg vul-ns' + (nsVul ? ' vul-vul' : ' vul-nv') + '">NS</span>' +
          '<span class="vul-seg vul-ew' + (ewVul ? ' vul-vul' : ' vul-nv') + '">EW</span>' +
          '</span>';
        row.innerHTML =
          '<div class="deal-info">' +
            '<span class="deal-board">' + escapeHtml(String(d.number)) + '</span>' +
            '<span class="deal-meta"><span class="deal-dealer">' + escapeHtml(d.dealer || '') + '</span> ' + vulLabel + '</span>' +
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
    document.querySelectorAll('.round-pill').forEach(function (el, i) {
      el.classList.toggle('selected', i === selectedRoundIndex);
    });
    if (btnSaveRound) {
      btnSaveRound.onclick = saveRoundResults;
    }
  }

  function renderRoundsList() {
    if (!schedule || !schedule.rounds.length) return;
    roundsList.innerHTML = '';
    schedule.rounds.forEach(function (rnd, i) {
      const pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'round-pill' + (i === 0 ? ' selected' : '');
      pill.textContent = 'Runda ' + rnd.round_number;
      pill.addEventListener('click', function () {
        setRound(i);
      });
      roundsList.appendChild(pill);
    });
  }

  linkEdit.href = '/tournament/' + encodeURIComponent(tourId);

  tablesList.addEventListener('input', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('deal-input')) scheduleHasUnsavedChanges = true;
  });
  tablesList.addEventListener('change', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('deal-input')) scheduleHasUnsavedChanges = true;
  });

  window.addEventListener('beforeunload', function (e) {
    if (scheduleHasUnsavedChanges) { e.preventDefault(); e.returnValue = ''; }
  });

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a || !scheduleHasUnsavedChanges) return;
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
    var input = e.target.closest('.deal-input');
    if (!input || !row.contains(input)) return;
    var focusables = getRowFocusables(row);
    var idx = focusables.indexOf(input);
    if (idx === -1) return;
    var allRows = Array.prototype.slice.call(tablesList.querySelectorAll('.deal-row'));

    if (e.key === 'Tab') {
      e.preventDefault();
      if (e.shiftKey) {
        if (idx > 0) {
          focusables[idx - 1].focus();
        } else {
          var rowIdx = allRows.indexOf(row);
          if (rowIdx > 0) {
            var prevRow = allRows[rowIdx - 1];
            var prevCard = prevRow.closest('.table-card-with-deals');
            if (prevCard && prevCard.classList.contains('collapsed')) {
              prevCard.querySelector('.table-card').click();
            }
            var lastInput = getRowFocusables(prevRow)[3];
            if (lastInput) setTimeout(function () { lastInput.focus(); }, 0);
          }
        }
      } else {
        if (idx < 3) {
          focusables[idx + 1].focus();
        } else {
          var rowIdx = allRows.indexOf(row);
          var nextRow = allRows[rowIdx + 1];
          if (nextRow) {
            var nextCard = nextRow.closest('.table-card-with-deals');
            if (nextCard && nextCard.classList.contains('collapsed')) {
              nextCard.querySelector('.table-card').click();
            }
            var firstInput = getRowFocusables(nextRow)[0];
            if (firstInput) setTimeout(function () { firstInput.focus(); }, 0);
          }
        }
      }
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      var rowIdx = allRows.indexOf(row);
      var nextRow = allRows[rowIdx + 1];
      if (nextRow) {
        var nextCard = nextRow.closest('.table-card-with-deals');
        if (nextCard && nextCard.classList.contains('collapsed')) {
          nextCard.querySelector('.table-card').click();
        }
        var firstInput = getRowFocusables(nextRow)[0];
        if (firstInput) setTimeout(function () { firstInput.focus(); }, 0);
      }
      return;
    }
  });

  fetch('/api/tournaments/' + encodeURIComponent(tourId) + '/schedule')
    .then(function (res) {
      if (!res.ok) {
        if (res.status === 404) {
          loadError.textContent = 'Turniej nie znaleziony.';
        } else {
          loadError.textContent = 'Błąd ładowania harmonogramu.';
        }
        loadError.classList.remove('hidden');
        return null;
      }
      return res.json();
    })
    .then(function (data) {
      if (!data) return;
      schedule = data;
      tournamentTitle.textContent = data.name || 'Harmonogram';
      scheduleMeta.textContent = 'Data: ' + (data.date || '');
      renderRoundsList();
      setRound(0);
      scheduleContent.classList.remove('hidden');
    });
})();
