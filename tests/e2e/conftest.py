"""
E2E (browser) test fixtures.
Starts the Flask app in a subprocess so tests run against a real server.
Use: pytest tests/e2e -v   (from project root)
Requires: pip install -r requirements-e2e.txt && playwright install
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Port for the E2E server (avoid 5000 if you run the app manually)
E2E_PORT = os.environ.get("E2E_PORT", "5764")
E2E_BASE_URL = os.environ.get("BASE_URL")  # If set, skip starting server


@pytest.fixture(scope="session")
def e2e_data_dir():
    """Temporary data directory for E2E; cleaned after session."""
    root = Path(__file__).resolve().parent.parent
    tmp = root / "tmp_e2e_data"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def flask_server(e2e_data_dir):
    """
    Start Flask app in a subprocess for E2E.
    If BASE_URL is set, use that and do not start a server.
    """
    if E2E_BASE_URL:
        yield E2E_BASE_URL
        return

    project_root = Path(__file__).resolve().parent.parent.parent
    env = os.environ.copy()
    env["BRIDGE_DATA_DIR"] = str(e2e_data_dir)
    env["PORT"] = E2E_PORT
    env["FLASK_DEBUG"] = "0"

    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=project_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base_url = f"http://127.0.0.1:{E2E_PORT}"
    deadline = time.monotonic() + 15
    import urllib.request
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url, timeout=1) as r:
                if r.status in (200, 302, 404):
                    break
        except Exception:
            if proc.poll() is not None:
                _, err = proc.communicate()
                pytest.fail(f"Flask exited early: {err.decode()}")
            time.sleep(0.2)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        pytest.fail("Flask server did not become ready in time")

    try:
        yield base_url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(flask_server):
    """Override pytest-playwright base_url to use our Flask server."""
    return flask_server
