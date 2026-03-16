"""
Shared pytest fixtures for tests/.
"""

import shutil
from pathlib import Path

import pytest

TESTS_API_DATA_DIR = Path(__file__).resolve().parent / "tmp_api_tournaments"


@pytest.fixture
def client():
    """Flask test client with DATA_DIR set to tests/tmp_api_tournaments (cleaned each run)."""
    import app as app_module
    from bridge.storage import ensure_data_dir

    data_dir = TESTS_API_DATA_DIR
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    ensure_data_dir(data_dir)
    original_data_dir = app_module.app.config["DATA_DIR"]
    app_module.app.config["DATA_DIR"] = data_dir
    app_module.app.config["TESTING"] = True
    try:
        yield app_module.app.test_client()
    finally:
        app_module.app.config["DATA_DIR"] = original_data_dir
        shutil.rmtree(data_dir, ignore_errors=True)
