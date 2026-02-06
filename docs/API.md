# Dokumentacja API

API aplikacji Turniej brydżowy. Wszystkie endpointy zwracają JSON. Baza URL: `http://127.0.0.1:5000` (lub inny host/port serwera).

Błędy: **404** – nie znaleziono, **400** – błąd walidacji, **503** – nie można odczytać danych turnieju.

---

## Ustawienia

### GET /api/settings

Zwraca bieżące ustawienia aplikacji.

**Odpowiedź 200:**
```json
{
  "debug_mode": false
}
```

### PATCH /api/settings

Aktualizuje ustawienia. Body: obiekt z dozwolonymi kluczami (np. `debug_mode`).

**Request:**
```json
{
  "debug_mode": true
}
```

**Odpowiedź 200:** jak GET /api/settings (zaktualizowane wartości).

---

## Turnieje

### GET /api/tournaments

Lista aktywnych turniejów (bez zarchiwizowanych).

**Odpowiedź 200:**
```json
[
  {
    "id": "uuid-turnieju",
    "name": "Puchar jesieni",
    "date": "2025-06-15",
    "archived": false
  }
]
```

### POST /api/tournaments

Tworzy nowy turniej.

**Request:**
```json
{
  "name": "Puchar jesieni 2025",
  "date": "2025-06-15",
  "teams": [
    { "name": "Alfa", "member1": "Jan Kowalski", "member2": "Anna Nowak" },
    { "name": "Beta", "member1": "Piotr Wiśniewski", "member2": "Maria Dąbrowska" }
  ],
  "num_rounds": 3,
  "deals_per_round": 2
}
```

- `name`, `date` – wymagane.
- `teams` – tablica obiektów z `name`, `member1`, `member2`; parzysta liczba drużyn (min. 2).
- `num_rounds` – opcjonalnie; bez tego używana jest domyślna liczba rund (round-robin).
- `deals_per_round` – opcjonalnie (domyślnie 2).

**Odpowiedź 200:**
```json
{
  "ok": true,
  "id": "uuid-turnieju",
  "name": "Puchar jesieni 2025",
  "date": "2025-06-15"
}
```

**Odpowiedź 400:** `{"ok": false, "errors": ["Nazwa jest wymagana.", ...]}`

### GET /api/tournaments/<tour_id>

Pobiera metadane turnieju i konfigurację cykli (do edycji).

**Odpowiedź 200:**
```json
{
  "id": "uuid",
  "name": "Puchar jesieni",
  "date": "2025-06-15",
  "teams": [
    { "name": "Alfa", "member1": "Jan", "member2": "Anna" }
  ],
  "cycles": [{ "deals_per_round": 2 }]
}
```

**Odpowiedź 404:** `{"error": "Nie znaleziono"}`

### PUT /api/tournaments/<tour_id>

Aktualizuje turniej (nazwa, data, drużyny, struktura rund). Body jak przy POST /api/tournaments.

**Odpowiedź 200:** `{"ok": true, "id": "...", "name": "...", "date": "..."}`  
**Odpowiedź 400:** `{"ok": false, "errors": [...]}`  
**Odpowiedź 404:** `{"ok": false, "errors": ["Turniej nie istnieje."]}`

### POST /api/tournaments/<tour_id>/archive

Archiwizuje turniej (znika z listy GET /api/tournaments).

**Odpowiedź 200:** `{"ok": true}`  
**Odpowiedź 404:** `{"ok": false, "error": "Nie znaleziono"}`

---

## Rundy i wyniki

### GET /api/tournaments/<tour_id>/rounds

Pełna struktura rund: stoliki, rozdania, zapisane wyniki per (stół, rozdanie).

**Odpowiedź 200:**
```json
{
  "id": "uuid",
  "name": "Puchar jesieni",
  "date": "2025-06-15",
  "rounds": [
    {
      "round_number": 1,
      "round_id": 1,
      "deals": [
        { "id": 1, "number": 1, "dealer": "N", "vulnerability": "None" }
      ],
      "tables": [
        {
          "table_number": 1,
          "ns_team": { "id": 1, "name": "Alfa" },
          "ew_team": { "id": 2, "name": "Beta" },
          "results": {
            "1": {
              "contract": "3NT",
              "declarer": "N",
              "opening_lead": "2H",
              "tricks_taken": 9,
              "ns_score": 400,
              "ew_score": 0
            }
          }
        }
      ]
    }
  ]
}
```

### POST /api/tournaments/<tour_id>/round-results

Zapisuje wyniki rozdań dla jednej rundy.

**Request:**
```json
{
  "round_id": 1,
  "results": [
    {
      "table_number": 1,
      "deal_id": 1,
      "contract": "3NT",
      "declarer": "N",
      "opening_lead": "2H",
      "tricks_taken": 9
    }
  ]
}
```

- `round_id` – wymagany (id rundy z GET …/rounds).
- `results` – tablica obiektów z: `table_number`, `deal_id`, `contract` (np. `3NT`, `4Sx`), `declarer` (N/S/E/W), `opening_lead`, `tricks_taken` (0–13).

**Odpowiedź 200:**
```json
{
  "ok": true,
  "saved": 2,
  "total": 2,
  "results": [
    { "ok": true, "ns_score": 400, "ew_score": 0 },
    { "ok": true, "ns_score": -50, "ew_score": 50 }
  ]
}
```

Dla wierszy z błędem walidacji: `{"ok": false, "error": "komunikat", "field": "contract"}` (lub inny `field`).

**Odpowiedź 400 (brak round_id):** `{"error": "Wymagane jest podanie identyfikatora rundy (round_id)."}`  
**Odpowiedź 404:** `{"error": "Nie znaleziono"}` lub `{"error": "Runda nie znaleziona"}`

### GET /api/tournaments/<tour_id>/rounds/<round_id>/deal-results

Wyniki rozdań w rundzie z IMP na rozdanie (do widoku „Wyniki”).

**Odpowiedź 200:** `{"deals_with_tables": [{ "deal": {...}, "table_rows": [...] }, ...]}`

### GET /api/tournaments/<tour_id>/rounds/<round_id>/ranking

Ranking kumulatywny IMP (rundy 1…N). Wymaga zapisanych wyników we wszystkich tych rundach.

**Odpowiedź 200:**
```json
{
  "round_number": 2,
  "round_numbers": [1, 2],
  "ranking": [
    { "team_name": "Alfa", "total_imp": 12, "round_imps": [5, 7] },
    { "team_name": "Beta", "total_imp": -12, "round_imps": [-5, -7] }
  ]
}
```

Gdy brak wyników: `{"round_number": 2, "error_message": "Nie wszystkie wyniki są zapisane...", "ranking": [], "round_numbers": []}`.

### GET /api/tournaments/<tour_id>/rounds/<round_id>/head-to-head

Macierz IMP drużyna vs drużyna (kumulatywnie do danej rundy).

**Odpowiedź 200:**
```json
{
  "round_number": 1,
  "team_names": ["Alfa", "Beta"],
  "matrix": [[0, 5], [-5, 0]]
}
```

`matrix[i][j]` = IMP drużyny `team_names[i]` przeciwko `team_names[j]`.

---

## Kontrakt i walidacja

### GET /api/contract-spec

Specyfikacja formatu kontraktu (poziomy, kolory, modyfikatory, wzorzec).

**Odpowiedź 200:**
```json
{
  "levels": [1, 2, 3, 4, 5, 6, 7],
  "suits": ["C", "D", "H", "S", "NT"],
  "modifiers": ["", "x", "xx"],
  "pattern": "^\\s*([1-7])\\s*(C|D|H|S|NT)\\s*(|x|xx)\\s*$"
}
```

### POST /api/validate-result

Waliduje pojedynczy wynik rozdania; zwraca punkty NS/EW.

**Request:**
```json
{
  "contract": "3NT",
  "declarer": "N",
  "opening_lead": "2H",
  "tricks_taken": 9,
  "vulnerability": "None"
}
```

**Odpowiedź 200 (OK):** `{"valid": true, "ns_score": 400, "ew_score": 0}`  
**Odpowiedź 200 (pas):** `{"valid": true, "ns_score": 0, "ew_score": 0}`  
**Odpowiedź 200 (błąd):** `{"valid": false, "errors": [{"field": "contract", "message": "..."}]}`

---

## Strony HTML (przeglądarka)

- `GET /` – lista turniejów
- `GET /tournament/<tour_id>` – edycja turnieju
- `GET /tournament/<tour_id>/rounds` – rundy i wyniki
- `GET /tournament/<tour_id>/schedule` – harmonogram
- `GET /tournament/<tour_id>/rounds/<round_id>/ranking` – przekierowanie do strony rund z zakładką ranking
