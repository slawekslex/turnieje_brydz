"""
Flask application entry point.
Tournaments are stored as JSON in the data/ directory.
"""

from pathlib import Path

from flask import Flask

from bridge.api import bp
from bridge.storage import ensure_data_dir

app = Flask(__name__)
app.config["DATA_DIR"] = Path(__file__).resolve().parent / "data"
app.register_blueprint(bp)


if __name__ == "__main__":
    ensure_data_dir(Path(app.config["DATA_DIR"]))
    app.run(debug=True, port=5000)
