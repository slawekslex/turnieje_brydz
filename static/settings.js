(function () {
  const btn = document.getElementById('btn-settings');
  const modal = document.getElementById('settings-modal');
  const overlay = document.getElementById('settings-overlay');
  const toggleDebug = document.getElementById('settings-debug-mode');
  const btnClose = document.getElementById('settings-close');

  if (!btn || !modal || !overlay) return;

  function openModal() {
    modal.classList.remove('hidden');
    loadSettings();
  }

  function closeModal() {
    modal.classList.add('hidden');
  }

  function loadSettings() {
    fetch('/api/settings')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        toggleDebug.checked = !!data.debug_mode;
      })
      .catch(function () {
        toggleDebug.checked = false;
      });
  }

  function saveDebugMode(value) {
    fetch('/api/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ debug_mode: value })
    }).catch(function () {});
  }

  btn.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);
  overlay.addEventListener('click', closeModal);

  if (toggleDebug) {
    toggleDebug.addEventListener('change', function () {
      saveDebugMode(toggleDebug.checked);
    });
  }
})();
