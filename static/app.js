(function () {
  const listSection = document.getElementById('tournament-list');
  const addSection = document.getElementById('add-tournament');
  const listEmpty = document.getElementById('list-empty');
  const tournamentsUl = document.getElementById('tournaments-ul');
  const btnAdd = document.getElementById('btn-add');
  const btnCancel = document.getElementById('btn-cancel');
  const form = document.getElementById('form-tournament');
  const teamsContainer = document.getElementById('teams-container');
  const btnAddTeam = document.getElementById('btn-add-team');
  const btnAutoTeams = document.getElementById('btn-auto-teams');
  const formErrors = document.getElementById('form-errors');
  const formSuccess = document.getElementById('form-success');
  const teamsSection = document.getElementById('teams-section');
  const teamsSectionHeader = document.getElementById('teams-section-header');
  const teamsSectionTitle = document.getElementById('teams-section-title');
  const teamsSectionToggle = document.getElementById('teams-section-toggle');
  const teamsSectionBody = document.getElementById('teams-section-body');
  const cyclesContainer = document.getElementById('cycles-container');
  const btnAddCycle = document.getElementById('btn-add-cycle');
  const roundsTotalsValue = document.getElementById('rounds-totals-value');

  function showList() {
    addSection.classList.add('hidden');
    listSection.classList.remove('hidden');
  }

  function showAdd() {
    listSection.classList.add('hidden');
    addSection.classList.remove('hidden');
    formErrors.classList.add('hidden');
    formSuccess.classList.add('hidden');
  }

  function loadTournaments() {
    fetch('/api/tournaments')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        listEmpty.classList.toggle('hidden', data.length > 0);
        tournamentsUl.innerHTML = '';
        data.forEach(function (t) {
          const li = document.createElement('li');
          li.className = 'tournament-row';
          const href = '/tournament/' + encodeURIComponent(t.id);
          li.innerHTML =
            '<a href="' + escapeHtml(href) + '" class="tournament-link">' +
              '<span><strong>' + escapeHtml(t.name) + '</strong></span>' +
              '<span class="tournament-date">' + escapeHtml(t.date) + '</span>' +
            '</a>' +
            '<button type="button" class="btn btn-archive btn-sm" data-id="' + escapeHtml(t.id) + '" title="Archiwizuj">Archiwizuj</button>';
          li.querySelector('.btn-archive').addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            var id = this.getAttribute('data-id');
            fetch('/api/tournaments/' + encodeURIComponent(id) + '/archive', { method: 'POST' })
              .then(function (res) { return res.json(); })
              .then(function (result) {
                if (result.ok) {
                  li.remove();
                  listEmpty.classList.toggle('hidden', tournamentsUl.querySelectorAll('li').length > 0);
                }
              });
          });
          tournamentsUl.appendChild(li);
        });
      })
      .catch(function () {
        listEmpty.textContent = 'Błąd ładowania listy turniejów.';
        listEmpty.classList.remove('hidden');
      });
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
      updateRoundsTotals();
    });
    teamsContainer.appendChild(block);
    updateTeamsSectionTitle();
    updateRoundsTotals();
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

  function setTeamsSectionCollapsed(collapsed) {
    if (collapsed) {
      teamsSection.classList.add('collapsed');
      teamsSectionToggle.textContent = '\u25B6';
    } else {
      teamsSection.classList.remove('collapsed');
      teamsSectionToggle.textContent = '\u25BC';
    }
    updateTeamsSectionTitle();
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

  function collectCycles() {
    const rows = cyclesContainer.querySelectorAll('.cycle-row');
    const cycles = [];
    rows.forEach(function (row) {
      var input = row.querySelector('.cycle-deals-input');
      var n = parseInt(input.value, 10);
      cycles.push({ deals_per_round: isNaN(n) || n < 0 ? 0 : n });
    });
    return cycles;
  }

  function addCycleRow(dealsPerRound) {
    var row = document.createElement('div');
    row.className = 'cycle-row';
    var idx = cyclesContainer.querySelectorAll('.cycle-row').length + 1;
    row.innerHTML =
      '<label>Cykl ' + idx + ':</label>' +
      '<input type="number" class="cycle-deals-input" min="0" value="' + (dealsPerRound != null ? dealsPerRound : 2) + '" placeholder="0">' +
      '<span class="cycle-deals-suffix">rozdania na rundę</span>' +
      '<button type="button" class="btn-remove-cycle">Usuń</button>';
    row.querySelector('.cycle-deals-input').addEventListener('input', updateRoundsTotals);
    row.querySelector('.cycle-deals-input').addEventListener('change', updateRoundsTotals);
    row.querySelector('.btn-remove-cycle').addEventListener('click', function () {
      row.remove();
      updateCycleLabels();
      updateRoundsTotals();
    });
    cyclesContainer.appendChild(row);
    updateRoundsTotals();
  }

  function updateCycleLabels() {
    var rows = cyclesContainer.querySelectorAll('.cycle-row');
    rows.forEach(function (row, i) {
      row.querySelector('label').textContent = 'Cykl ' + (i + 1) + ':';
    });
  }

  function updateRoundsTotals() {
    var numTeams = getTeamCount();
    var cycles = collectCycles();
    if (numTeams < 2 || numTeams % 2 !== 0) {
      roundsTotalsValue.textContent = '— rund, — rozdania (dodaj parzystą liczbę drużyn)';
      return;
    }
    var roundsPerCycle = numTeams - 1;
    var totalRounds = cycles.length * roundsPerCycle;
    var totalDeals = 0;
    cycles.forEach(function (c) {
      totalDeals += roundsPerCycle * (c.deals_per_round || 0);
    });
    roundsTotalsValue.textContent = totalRounds + ' rund, ' + totalDeals + ' rozdania';
  }

  teamsSectionToggle.textContent = '\u25BC';

  teamsSectionHeader.addEventListener('click', function () {
    var collapsed = teamsSection.classList.toggle('collapsed');
    teamsSectionToggle.textContent = collapsed ? '\u25B6' : '\u25BC';
    updateTeamsSectionTitle();
  });

  btnAdd.addEventListener('click', function () {
    teamsContainer.innerHTML = '';
    cyclesContainer.innerHTML = '';
    addTeamBlock({});
    addTeamBlock({});
    addCycleRow(2);
    updateCycleLabels();
    form.reset();
    document.getElementById('tournament-date').value = new Date().toISOString().slice(0, 10);
    setTeamsSectionCollapsed(false);
    updateTeamsSectionTitle();
    updateRoundsTotals();
    showAdd();
  });

  btnCancel.addEventListener('click', showList);

  btnAddTeam.addEventListener('click', function () {
    addTeamBlock({});
  });

  btnAddCycle.addEventListener('click', function () {
    addCycleRow(2);
    updateCycleLabels();
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

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    formErrors.classList.add('hidden');
    formSuccess.classList.add('hidden');

    const name = (document.getElementById('tournament-name').value || '').trim();
    const date = document.getElementById('tournament-date').value;
    const teams = collectTeams();
    const cycles = collectCycles();

    fetch('/api/tournaments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, date: date, teams: teams, cycles: cycles.length ? cycles : [{ deals_per_round: 2 }] })
    })
      .then(function (res) { return res.json().then(function (data) { return { res: res, data: data }; }); })
      .then(function (result) {
        if (!result.res.ok) {
          const err = result.data;
          const msg = (err.errors && err.errors.length) ? err.errors.join('\n') : 'Wystąpił błąd.';
          formErrors.innerHTML = '<ul><li>' + (err.errors || [msg]).map(escapeHtml).join('</li><li>') + '</li></ul>';
          formErrors.classList.remove('hidden');
          return;
        }
        formSuccess.textContent = 'Turniej „' + escapeHtml(result.data.name) + '” został utworzony.';
        formSuccess.classList.remove('hidden');
        loadTournaments();
        setTimeout(function () {
          window.location.href = '/tournament/' + encodeURIComponent(result.data.id) + '/schedule';
        }, 800);
      })
      .catch(function () {
        formErrors.textContent = 'Błąd połączenia. Spróbuj ponownie.';
        formErrors.classList.remove('hidden');
      });
  });

  loadTournaments();
})();
