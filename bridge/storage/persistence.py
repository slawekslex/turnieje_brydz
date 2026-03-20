"""
Tournament persistence: save/load JSON files; discover by scanning data dir.
Each tournament lives in its own folder: data/$TOURNAMENT_NAME$DATE/data.json
with an archive/ subfolder for timestamped backups before each write.
No index.json: we walk the data directory and read id/name/date/archived from each data.json.
"""

import json
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from bridge.models.tournament import (
    Tournament,
    tournament_from_dict,
    tournament_to_dict,
)


def ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def _iter_tournament_data_paths(data_dir: Path):
    """Yield (data_path, raw_data) for each tournament folder (subdir containing data.json)."""
    ensure_data_dir(data_dir)
    for child in data_dir.iterdir():
        if not child.is_dir():
            continue
        data_path = child / "data.json"
        if not data_path.exists():
            continue
        try:
            with data_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        yield data_path, data


def get_tournament_data_path(data_dir: Path, tour_id: str) -> Path | None:
    """Resolve tournament id to data.json path by scanning data dir. Returns None if not found."""
    ensure_data_dir(data_dir)
    for data_path, data in _iter_tournament_data_paths(data_dir):
        if data.get("id") == tour_id:
            return data_path
    return None


def list_tournament_entries(data_dir: Path) -> list:
    """List all tournaments: scan data dir and return [{ id, name, date, archived }, ...]."""
    ensure_data_dir(data_dir)
    entries = []
    for _path, data in _iter_tournament_data_paths(data_dir):
        entries.append({
            "id": data.get("id"),
            "name": data.get("name") or "",
            "date": data.get("date") or "",
            "archived": data.get("archived", False),
        })
    return entries


def tournament_folder_name(name: str, date_str: str, tour_id: str, data_dir: Path) -> str:
    """
    Build a filesystem-safe folder name: $TOURNAMENT_NAME$DATE.
    Sanitizes name; if folder already exists for another id, appends _<short_id>.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip() or "tournament"
    base_folder = f"{sanitized}_{date_str}"
    folder = base_folder
    existing = data_dir / folder
    if existing.exists():
        folder = f"{base_folder}_{tour_id[:8]}"
    return folder


def ensure_tournament_dir(data_dir: Path, folder: str) -> Path:
    """Create tournament folder and archive subfolder. Returns path to tournament dir."""
    tour_dir = data_dir / folder
    tour_dir.mkdir(parents=True, exist_ok=True)
    (tour_dir / "archive").mkdir(exist_ok=True)
    return tour_dir


def _archive_existing_data(path: Path) -> None:
    """If data.json exists, copy it to archive/ with current timestamp before overwriting."""
    path = Path(path)
    if not path.exists():
        return
    archive_dir = path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, archive_dir / f"{ts}.json")


def save_tournament(
    tournament: Tournament,
    path: Path | str,
    cycles: list | None = None,
    *,
    tour_id: str | None = None,
    archived: bool | None = None,
) -> None:
    """Save a tournament to a JSON file. Optionally include cycles config.
    Before writing, copies existing file to archive/ with timestamp if it exists.
    Writes id and archived into the JSON (for discovery when scanning); when creating
    pass tour_id; when updating/archiving we read existing id/archived from file."""
    path = Path(path)
    _archive_existing_data(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = tournament_to_dict(tournament)
    if cycles is not None:
        data["cycles"] = cycles
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            data["id"] = existing.get("id")
            data["archived"] = (
                archived if archived is not None else existing.get("archived", False)
            )
        except (json.JSONDecodeError, OSError):
            data["id"] = tour_id
            data["archived"] = archived if archived is not None else False
    else:
        data["id"] = tour_id
        data["archived"] = archived if archived is not None else False
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
_settings_lock = threading.RLock()
_settings_runtime_cache: dict[str, dict] = {}
_settings_mtime_cache: dict[str, int | None] = {}


def _settings_path(data_dir: Path) -> Path:
    return data_dir / "settings.json"


def load_settings(data_dir: Path) -> dict:
    """Load app settings from data/settings.json with runtime cache sync."""
    ensure_data_dir(data_dir)
    path = _settings_path(data_dir)
    cache_key = str(path.resolve())
    with _settings_lock:
        if not path.exists():
            defaults = dict(DEFAULT_SETTINGS)
            _settings_runtime_cache[cache_key] = defaults
            _settings_mtime_cache[cache_key] = None
            return dict(defaults)
        try:
            current_mtime = path.stat().st_mtime_ns
        except OSError:
            defaults = dict(DEFAULT_SETTINGS)
            _settings_runtime_cache[cache_key] = defaults
            _settings_mtime_cache[cache_key] = None
            return dict(defaults)
        cached_mtime = _settings_mtime_cache.get(cache_key)
        if cache_key in _settings_runtime_cache and cached_mtime == current_mtime:
            return dict(_settings_runtime_cache[cache_key])
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, OSError):
            merged = dict(DEFAULT_SETTINGS)
        _settings_runtime_cache[cache_key] = merged
        _settings_mtime_cache[cache_key] = current_mtime
        return dict(merged)


def save_settings(data_dir: Path, settings: dict) -> None:
    """Save app settings, and refresh runtime cache atomically."""
    ensure_data_dir(data_dir)
    path = _settings_path(data_dir)
    cache_key = str(path.resolve())
    with _settings_lock:
        current = load_settings(data_dir)
        current.update(settings)
        with path.open("w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            mtime = None
        _settings_runtime_cache[cache_key] = dict(current)
        _settings_mtime_cache[cache_key] = mtime
