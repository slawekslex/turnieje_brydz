# Storage without index.json

Tournament list and lookup now use **directory scanning** instead of `index.json`.

## Behaviour

- **Discovery**: Walk `data/`; every subdirectory that contains `data.json` is a tournament.
- **Lookup by id**: Scan each `data.json` and match `data["id"]` to the requested `tour_id`.
- **List**: `list_tournament_entries(data_dir)` returns `[{ id, name, date, archived }, ...]` from the scanned files.
- **id and archived** are stored inside each `data.json`, so no separate index is needed.

## API changes for routes

1. **List tournaments**  
   Use `list_tournament_entries(_data_dir())` instead of `load_index(_data_dir())`.  
   Filter by `archived` as before:  
   `active = [e for e in entries if not e.get("archived")]`.

2. **Create tournament**  
   - Create folder and `data.json` as before.  
   - Call `save_tournament(tournament, path, cycles=cycles, tour_id=tour_id)`.  
   - Do **not** call `save_index` or maintain the index.

3. **Update tournament**  
   Resolve path with `get_tournament_data_path(_data_dir(), tour_id)` (scan).  
   Call `save_tournament(...)` as usual; `id` and `archived` are preserved from the existing file.

4. **Archive tournament**  
   Resolve path, then:  
   `save_tournament(tournament, path, cycles=load_tournament_cycles(path), archived=True)`.

## Exports

- **Removed**: `load_index`, `save_index`
- **Added**: `list_tournament_entries(data_dir) -> list`
- **Changed**: `save_tournament(..., tour_id=..., archived=...)` — when creating, pass `tour_id`; when archiving, pass `archived=True`.
