(function () {
  if (window.BridgeSettings) return;

  var state = { debug_mode: false };
  var listeners = [];
  var initialized = false;
  var inFlightLoad = null;
  var inFlightSave = null;

  function normalize(data) {
    return { debug_mode: !!(data && data.debug_mode) };
  }

  function emit(next) {
    var payload = normalize(next);
    state = payload;
    document.dispatchEvent(new CustomEvent('settingsChanged', { detail: payload }));
    document.dispatchEvent(new CustomEvent('debugModeChanged', { detail: payload }));
    listeners.forEach(function (cb) {
      try {
        cb(payload);
      } catch (_err) {
        // Ignore subscriber exceptions to keep store stable.
      }
    });
  }

  function loadFromApi() {
    if (inFlightLoad) return inFlightLoad;
    inFlightLoad = fetch('/api/settings')
      .then(function (res) {
        if (!res.ok) throw new Error('settings_load_failed');
        return res.json();
      })
      .then(function (data) {
        emit(data);
        initialized = true;
        return state;
      })
      .finally(function () {
        inFlightLoad = null;
      });
    return inFlightLoad;
  }

  function patchToApi(partial) {
    if (inFlightSave) return inFlightSave;
    inFlightSave = fetch('/api/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(partial || {})
    })
      .then(function (res) {
        if (!res.ok) throw new Error('settings_save_failed');
        return res.json();
      })
      .then(function (data) {
        emit(data);
        initialized = true;
        return state;
      })
      .finally(function () {
        inFlightSave = null;
      });
    return inFlightSave;
  }

  window.BridgeSettings = {
    ready: function () {
      if (initialized) return Promise.resolve(state);
      return loadFromApi();
    },
    get: function () {
      return normalize(state);
    },
    reload: function () {
      return loadFromApi();
    },
    update: function (partial) {
      return patchToApi(partial);
    },
    subscribe: function (cb) {
      if (typeof cb !== 'function') return function () {};
      listeners.push(cb);
      cb(normalize(state));
      return function () {
        listeners = listeners.filter(function (it) { return it !== cb; });
      };
    }
  };

  // Keep runtime settings fresh when user returns to the tab.
  window.addEventListener('focus', function () {
    loadFromApi().catch(function () {});
  });

  loadFromApi().catch(function () {});
})();
