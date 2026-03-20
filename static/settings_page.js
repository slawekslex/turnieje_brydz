(function () {
  var store = window.BridgeSettings;
  var debugToggle = document.getElementById('settings-debug-mode');
  var statusEl = document.getElementById('settings-save-status');

  if (!store || !debugToggle) return;

  function setStatus(text, type) {
    if (!statusEl) return;
    statusEl.textContent = text || '';
    statusEl.classList.remove('settings-status--ok', 'settings-status--error');
    if (type === 'ok') statusEl.classList.add('settings-status--ok');
    if (type === 'error') statusEl.classList.add('settings-status--error');
  }

  function render(settings) {
    debugToggle.checked = !!(settings && settings.debug_mode);
  }

  store.ready()
    .then(function (settings) {
      render(settings);
    })
    .catch(function () {
      setStatus('Nie udalo sie zaladowac ustawien.', 'error');
    });

  store.subscribe(render);

  debugToggle.addEventListener('change', function () {
    var nextValue = debugToggle.checked;
    setStatus('Zapisywanie...', null);
    store.update({ debug_mode: nextValue })
      .then(function () {
        setStatus('Zapisano.', 'ok');
      })
      .catch(function () {
        setStatus('Blad zapisu. Sprobuj ponownie.', 'error');
      });
  });
})();
