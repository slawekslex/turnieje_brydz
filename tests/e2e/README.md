# E2E (browser) tests

End-to-end tests run the app in a real browser (Chromium via Playwright). The `page` fixture comes from the **pytest-playwright** plugin, so you must run in a way that loads it.

## 1. Use the project root

All commands below must be run from the **repository root** (the folder that contains `app.py`, `pytest.ini`, and `tests/`). That way pytest finds `pytest.ini`, discovers the playwright plugin, and loads `tests/e2e/conftest.py` correctly.

```bash
cd path\to\turnieje_brydz
```

## 2. Same environment as your app

Use the same Python environment where you installed the E2E deps. If you use a venv, activate it first so `pytest` and `pytest-playwright` are available.

## 3. Install E2E deps and browsers

```bash
pip install -r requirements-e2e.txt
python -m playwright install chromium
```

## 4. Run the E2E tests

From the **project root**, run:

```bash
python -m pytest tests/e2e -v
```

Using `python -m pytest` (instead of plain `pytest`) makes sure the correct interpreter and installed packages are used, so the **pytest-playwright** plugin is loaded and provides the `page`, `browser`, and `base_url` fixtures.

- To use an already-running server: `set BASE_URL=http://localhost:5000` (Windows) or `export BASE_URL=http://localhost:5000` (Linux/macOS), then run the same command.

### See what’s happening in the browser

- **Show the browser window**: add `--headed` so Chromium runs with a visible window instead of headless:
  ```bash
  python -m pytest tests/e2e -v --headed
  ```
- **Slow down actions** so you can follow (milliseconds per action):
  ```bash
  python -m pytest tests/e2e -v --headed --slowmo 1000
  ```
- **Pause before closing** (handy with headed): add `--pause-on-failure` or use Playwright’s debug mode: set env `PWDEBUG=1` then run pytest (browser stays open and you get the Playwright Inspector).

- **Only Chromium**: add `-k chromium` if you didn’t install Firefox/WebKit.
