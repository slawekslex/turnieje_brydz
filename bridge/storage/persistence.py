"""
Tournament persistence: save/load JSON files and index.
"""

import json
from pathlib import Path

from bridge.models.tournament import (
    Tournament,
    tournament_from_dict,
    tournament_to_dict,
)


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    index_file = data_dir / "index.json"
    if not index_file.exists():
        index_file.write_text("[]", encoding="utf-8")


def load_index(data_dir: Path) -> list:
    ensure_data_dir(data_dir)
    index_file = data_dir / "index.json"
    with index_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_index(data_dir: Path, entries: list) -> None:
    ensure_data_dir(data_dir)
    index_file = data_dir / "index.json"
    with index_file.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def save_tournament(
    tournament: Tournament,
    path: Path | str,
    cycles: list | None = None,
) -> None:
    """Save a tournament to a JSON file. Optionally include cycles config."""
    path = Path(path)
    data = tournament_to_dict(tournament)
    if cycles is not None:
        data["cycles"] = cycles
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_tournament(path: Path | str) -> Tournament:
    """Load a tournament from a JSON file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return tournament_from_dict(data)


def load_tournament_cycles(path: Path | str) -> list:
    """Load the cycles config from a tournament JSON file. Default: one cycle, 2 deals/round."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cycles", [{"deals_per_round": 2}])


DEFAULT_SETTINGS = {"debug_mode": False}


def _settings_path(data_dir: Path) -> Path:
    return data_dir / "settings.json"


def load_settings(data_dir: Path) -> dict:
    """Load app settings from data/settings.json. Returns defaults if missing."""
    ensure_data_dir(data_dir)
    path = _settings_path(data_dir)
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_SETTINGS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(data_dir: Path, settings: dict) -> None:
    """Save app settings to data/settings.json. Merges with existing, then writes."""
    ensure_data_dir(data_dir)
    current = load_settings(data_dir)
    current.update(settings)
    path = _settings_path(data_dir)
    with path.open("w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
