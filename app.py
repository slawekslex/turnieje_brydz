"""
Flask application entry point.
Tournaments are stored as JSON in the data/ directory.

Configuration: load from .env (if present), then override with environment variables.
See .env.example for available keys (BRIDGE_DATA_DIR, FLASK_DEBUG, PORT, FLASK_SECRET_KEY).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from bridge.api import bp
from bridge.storage import ensure_data_dir

# Load .env from project root (next to app.py) at startup
_load_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_load_env_path)

# --- Config from environment (after .env) ---
_default_data_dir = Path(__file__).resolve().parent / "data"
_data_dir_str = os.environ.get("BRIDGE_DATA_DIR")
DATA_DIR = Path(_data_dir_str) if _data_dir_str else _default_data_dir

_debug_str = (os.environ.get("FLASK_DEBUG") or "").strip().lower()
DEBUG = _debug_str in ("1", "true", "yes", "on")

_port_str = os.environ.get("PORT", "5000")
try:
    PORT = int(_port_str)
except ValueError:
    PORT = 5000

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or None

app = Flask(__name__)
app.config["DATA_DIR"] = DATA_DIR
if SECRET_KEY is not None:
    app.config["SECRET_KEY"] = SECRET_KEY
app.register_blueprint(bp)


if __name__ == "__main__":
    ensure_data_dir(Path(app.config["DATA_DIR"]))
    app.run(debug=DEBUG, port=PORT)
