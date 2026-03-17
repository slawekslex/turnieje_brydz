(function () {
  const tourId = window.TOUR_ID;
  const form = document.getElementById('form-tournament');
  const teamsContainer = document.getElementById('teams-container');
  const btnAddTeam = document.getElementById('btn-add-team');
  const btnAutoTeams = document.getElementById('btn-auto-teams');
  const formErrors = document.getElementById('form-errors');
  const formSuccess = document.getElementById('form-success');
  const loadError = document.getElementById('load-error');
  const teamsSection = document.getElementById('teams-section');
  const teamsSectionHeader = document.getElementById('teams-section-header');
  const teamsSectionTitle = document.getElementById('teams-section-title');
  const teamsSectionToggle = document.getElementById('teams-section-toggle');
  const numRoundsInput = document.getElementById('tournament-num-rounds');
  const dealsPerRoundInput = document.getElementById('tournament-deals-per-round');
  const numberOfBoxesInput = document.getElementById('tournament-number-of-boxes');
  const roundsWarning = document.getElementById('rounds-warning');
  const roundsTotalsValue = document.getElementById('rounds-totals');
  const inProgressHint = document.getElementById('in-progress-hint');

  function setInProgressLock(hasResults) {
    if (inProgressHint) {
      inProgressHint.classList.toggle('hidden', !hasResults);
      inProgressHint.textContent = hasResults
        ? 'Turniej ma zapisane wyniki. Zmiana nazwy drużyn lub dodanie rund zachowa wyniki. Dodanie/usunięcie drużyny, zmniejszenie rund lub zmiana rozdań na rundę wyczyści wyniki (zostaniesz poproszony o potwierdzenie).'
        : '';
    }
    if (btnAddTeam) {
      btnAddTeam.disabled = false;
      btnAddTeam.title = hasResults ? 'Dodanie drużyny wyczyści zapisane wyniki (potwierdzenie przy zapisie).' : '';
    }
    if (teamsContainer) {
      teamsContainer.querySelectorAll('.btn-remove-team').forEach(function (btn) {
        btn.disabled = false;
        btn.title = hasResults ? 'Usunięcie drużyny wyczyści zapisane wyniki (potwierdzenie przy zapisie).' : '';
      });
    }
    if (numRoundsInput) {
      numRoundsInput.disabled = false;
      numRoundsInput.title = hasResults ? 'Możesz zwiększyć liczbę rund (zachowa wyniki) lub zmniejszyć (wymaga potwierdzenia, jeśli usuwane rundy mają wyniki).' : '';
    }
    if (dealsPerRoundInput) {
      dealsPerRoundInput.disabled = false;
      dealsPerRoundInput.title = hasResults ? 'Zmiana liczby rozdań na rundę wyczyści zapisane wyniki (potwierdzenie przy zapisie).' : '';
    }
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function addTeamBlock(team) {
    const block = document.createElement('div');
    block.className = 'team-block';
    block.innerHTML =
      '<input type="text" class="team-name" placeholder="Nazwa drużyny" name="team_name" value="' + escapeHtml(team.name || '') + '">' +
      '<input type="text" class="member1" placeholder="Członek 1" name="member1" value="' + escapeHtml(team.member1 || '') + '">' +
      '<input type="text" class="member2" placeholder="Członek 2" name="member2" value="' + escapeHtml(team.member2 || '') + '">' +
      '<button type="button" class="btn-remove-team">Usuń</button>';
    block.querySelector('.btn-remove-team').addEventListener('click', function () {
      block.remove();
      updateTeamsSectionTitle();
      updateRoundsSummary();
    });
    teamsContainer.appendChild(block);
    updateTeamsSectionTitle();
    updateRoundsSummary();
  }

  function getTeamCount() {
    return teamsContainer.querySelectorAll('.team-block').length;
  }

  function updateTeamsSectionTitle() {
    var n = getTeamCount();
    if (teamsSection.classList.contains('collapsed')) {
      teamsSectionTitle.textContent = n === 1 ? 'Drużyny (1 drużyna)' : 'Drużyny (' + n + ' drużyn)';
    } else {
      teamsSectionTitle.textContent = 'Drużyny';
    }
  }

  function collectTeams() {
    const blocks = teamsContainer.querySelectorAll('.team-block');
    const teams = [];
    blocks.forEach(function (block) {
      const name = (block.querySelector('.team-name').value || '').trim();
      const member1 = (block.querySelector('.member1').value || '').trim();
      const member2 = (block.querySelector('.member2').value || '').trim();
      teams.push({ name: name, member1: member1, member2: member2 });
    });
    return teams;
  }

  function updateRoundsSummary() {
    var numTeams = getTeamCount();
    var numRounds = parseInt(numRoundsInput && numRoundsInput.value !== '' ? numRoundsInput.value : '0', 10);
    var dealsPerRound = parseInt(dealsPerRoundInput && dealsPerRoundInput.value !== '' ? dealsPerRoundInput.value : '0', 10);
    if (isNaN(numRounds)) numRounds = 0;
    if (isNaN(dealsPerRound)) dealsPerRound = 0;
    // Even teams: (n-1) rounds per full round-robin; odd teams: n rounds per cycle (one bye per round)
    var roundsPerCycle = numTeams >= 2 ? (numTeams % 2 === 0 ? numTeams - 1 : numTeams) : 0;

    if (roundsWarning) {
      if (numTeams >= 2 && roundsPerCycle > 0 && numRounds > 0 && numRounds % roundsPerCycle !== 0) {
        roundsWarning.textContent = 'Liczba rund (' + numRounds + ') nie jest wielokrotnością rund w cyklu (' + roundsPerCycle + '). Ostatnia seria round-robin będzie niepełna. Możesz zapisać.';
        roundsWarning.classList.remove('hidden');
      } else {
        roundsWarning.textContent = '';
        roundsWarning.classList.add('hidden');
      }
    }

    if (roundsTotalsValue) {
      if (numTeams < 2) {
        roundsTotalsValue.textContent = 'Dodaj co najmniej 2 drużyny.';
      } else {
        var totalDeals = numRounds * dealsPerRound;
        roundsTotalsValue.textContent = numRounds + ' rund, ' + totalDeals + ' rozdania';
      }
    }
  }

  teamsSectionToggle.textContent = '\u25BC';

  teamsSectionHeader.addEventListener('click', function () {
    var collapsed = teamsSection.classList.toggle('collapsed');
    teamsSectionToggle.textContent = collapsed ? '\u25B6' : '\u25BC';
    updateTeamsSectionTitle();
  });

  btnAddTeam.addEventListener('click', function () {
    addTeamBlock({});
  });

  if (numRoundsInput) {
    numRoundsInput.addEventListener('input', updateRoundsSummary);
    numRoundsInput.addEventListener('change', updateRoundsSummary);
  }
  if (dealsPerRoundInput) {
    dealsPerRoundInput.addEventListener('input', updateRoundsSummary);
    dealsPerRoundInput.addEventListener('change', updateRoundsSummary);
  }

  function setAutoButtonVisibility(debugMode) {
    if (btnAutoTeams) btnAutoTeams.style.display = debugMode ? '' : 'none';
  }
  setAutoButtonVisibility(false);

  fetch('/api/settings')
    .then(function (res) { return res.json(); })
    .then(function (data) { setAutoButtonVisibility(!!data.debug_mode); })
    .catch(function () { setAutoButtonVisibility(false); });
  document.addEventListener('debugModeChanged', function (e) {
    setAutoButtonVisibility(!!(e.detail && e.detail.debug_mode));
  });

  btnAutoTeams.addEventListener('click', function (e) {
    e.stopPropagation();
    const blocks = teamsContainer.querySelectorAll('.team-block');
    const n = blocks.length;
    if (n === 0) {
      for (var i = 0; i < 4; i++) {
        addTeamBlock({
          name: 'Drużyna ' + (i + 1),
          member1: 'Gracz ' + (i + 1) + 'A',
          member2: 'Gracz ' + (i + 1) + 'B'
        });
      }
      return;
    }
    blocks.forEach(function (block, i) {
      var nameEl = block.querySelector('.team-name');
      var m1El = block.querySelector('.member1');
      var m2El = block.querySelector('.member2');
      if (!(nameEl.value || '').trim()) nameEl.value = 'Drużyna ' + (i + 1);
      if (!(m1El.value || '').trim()) m1El.value = 'Gracz ' + (i + 1) + 'A';
      if (!(m2El.value || '').trim()) m2El.value = 'Gracz ' + (i + 1) + 'B';
    });
    updateTeamsSectionTitle();
  });

  function buildPayload() {
    const name = (document.getElementById('tournament-name').value || '').trim();
    const date = document.getElementById('tournament-date').value;
    const teams = collectTeams();
    const numRounds = parseInt(numRoundsInput && numRoundsInput.value !== '' ? numRoundsInput.value : '0', 10);
    const dealsPerRound = parseInt(dealsPerRoundInput && dealsPerRoundInput.value !== '' ? dealsPerRoundInput.value : '2', 10);
    const numberOfBoxes = parseInt(numberOfBoxesInput && numberOfBoxesInput.value !== '' ? numberOfBoxesInput.value : '16', 10);
    return {
      name: name,
      date: date,
      teams: teams,
      num_rounds: isNaN(numRounds) ? 0 : Math.max(0, numRounds),
      deals_per_round: isNaN(dealsPerRound) ? 2 : Math.max(0, dealsPerRound),
      number_of_boxes: isNaN(numberOfBoxes) ? 16 : Math.max(1, numberOfBoxes)
    };
  }

  function doSubmit(payload, confirmClearResults) {
    if (confirmClearResults) {
      payload = Object.assign({}, payload, { confirm_clear_results: true });
    }
    return fetch('/api/tournaments/' + encodeURIComponent(tourId), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) { return res.json().then(function (data) { return { res: res, data: data }; }); })
      .then(function (result) {
        if (result.res.status === 409 && result.data.breaking_change) {
          var msg = (result.data.message || 'Ta zmiana usunie zapisane wyniki.') + '\n\n' + (result.data.errors || []).join('\n');
          if (!window.confirm(msg + '\n\nKontynuować i wyczyścić wyniki?')) {
            return;
          }
          return doSubmit(buildPayload(), true);
        }
        if (!result.res.ok) {
          const err = result.data;
          const msg = (err.errors && err.errors.length) ? err.errors.join('\n') : 'Wystąpił błąd.';
          formErrors.innerHTML = '<ul><li>' + (err.errors || [msg]).map(escapeHtml).join('</li><li>') + '</li></ul>';
          formErrors.classList.remove('hidden');
          return;
        }
        formSuccess.textContent = 'Turniej „' + escapeHtml(result.data.name) + '” został zapisany.';
        formSuccess.classList.remove('hidden');
      })
      .catch(function () {
        formErrors.textContent = 'Błąd połączenia. Spróbuj ponownie.';
        formErrors.classList.remove('hidden');
      });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    formErrors.classList.add('hidden');
    formSuccess.classList.add('hidden');

    const payload = buildPayload();
    if (payload.num_rounds < 0) {
      formErrors.textContent = 'Podaj prawidłową liczbę rund (0 lub więcej).';
      formErrors.classList.remove('hidden');
      return;
    }

    doSubmit(payload, false);
  });

  fetch('/api/tournaments/' + encodeURIComponent(tourId))
    .then(function (res) {
      if (!res.ok) {
        if (res.status === 404) {
          loadError.textContent = 'Turniej nie znaleziony.';
        } else {
          loadError.textContent = 'Błąd ładowania turnieju.';
        }
        loadError.classList.remove('hidden');
        return null;
      }
      return res.json();
    })
    .then(function (data) {
      if (!data) return;
      var breadcrumbName = document.getElementById('breadcrumb-tournament-name');
      if (breadcrumbName) breadcrumbName.textContent = data.name || 'Turniej';
      document.getElementById('tournament-name').value = data.name || '';
      document.getElementById('tournament-date').value = data.date || '';
      teamsContainer.innerHTML = '';
      (data.teams || []).forEach(function (t) {
        addTeamBlock({ name: t.name, member1: t.member1, member2: t.member2 });
      });
      if (getTeamCount() === 0) {
        addTeamBlock({});
        addTeamBlock({});
      }
      if (numRoundsInput) numRoundsInput.value = data.num_rounds != null ? String(data.num_rounds) : '3';
      if (dealsPerRoundInput) dealsPerRoundInput.value = data.deals_per_round != null ? String(data.deals_per_round) : '2';
      if (numberOfBoxesInput) numberOfBoxesInput.value = data.number_of_boxes != null ? String(data.number_of_boxes) : '16';
      updateRoundsSummary();
      setInProgressLock(!!data.has_results);
      form.classList.remove('hidden');
      updateTeamsSectionTitle();
    });
})();
