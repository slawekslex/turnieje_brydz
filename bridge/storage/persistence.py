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


def save_tournament(tournament: Tournament, path: Path | str) -> None:
    """Save a tournament to a JSON file."""
    path = Path(path)
    data = tournament_to_dict(tournament)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_tournament(path: Path | str) -> Tournament:
    """Load a tournament from a JSON file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return tournament_from_dict(data)
