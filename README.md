# Turniej brydżowy

**Wersja 0.3.0**

Aplikacja webowa do zarządzania turniejami brydżowymi w systemie round-robin: lista turniejów, tworzenie i edycja (metadane + drużyny), harmonogram rund i rozdania generowane automatycznie, wpisywanie wyników rozdania z walidacją kontraktu i liczeniem IMP, ranking kumulatywny oraz macierz head-to-head.

## Zrzuty ekranu

![Lista turniejów](screenshots/Screenshot%202026-02-06%20143158.png)
![Harmonogram](screenshots/Screenshot%202026-02-06%20143319.png)
![Rundy i wyniki](screenshots/Screenshot%202026-02-06%20143534.png)

## Wymagania

- Python 3.10+

## Instalacja i uruchomienie

1. **Środowisko wirtualne (zalecane):**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # Linux / macOS
   ```

2. **Instalacja zależności:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Uruchomienie serwera:**

   ```bash
   python app.py
   ```

4. Otwórz w przeglądarce: **http://127.0.0.1:5000/**

**Konfiguracja:** Skopiuj `.env.example` do `.env` w katalogu projektu i ustaw wartości. Aplikacja ładuje `.env` przy starcie; zmienne środowiskowe mają pierwszeństwo.

| Zmienna           | Opis                          | Domyślnie      |
|-------------------|-------------------------------|----------------|
| `BRIDGE_DATA_DIR` | Katalog z danymi (turnieje)   | `./data`       |
| `FLASK_DEBUG`     | Tryb debug (`true`/`1`/`yes`) | `false`        |
| `PORT`            | Port serwera                  | `5000`         |
| `FLASK_SECRET_KEY`| Klucz sekretny (sesje; produkcja) | —          |

## Funkcjonalność

### Turnieje

- **Lista turniejów** — strona główna: lista aktywnych turniejów (nazwa, data). Turnieje zarchiwizowane nie są na liście.
- **Dodaj turniej** — formularz: nazwa, data, drużyny (nazwa + dwóch członków). Liczba drużyn parzysta (min. 2). Przycisk „+ Drużyna” dodaje kolejną drużynę.
- **Edycja turnieju** — zmiana nazwy, daty i drużyn (z zachowaniem spójności rund).
- **Archiwizacja** — ukrycie turnieju z listy (dane pozostają w `data/`).

Po zapisaniu turnieju generowany jest harmonogram rund (round-robin) oraz rozdania; dane zapisywane są w katalogu `data/` (jeden folder na turniej, plik `data.json`; brak pliku indeksu — skan katalogu).

### Rundy i wyniki

- **Harmonogram** — strona „Harmonogram” (`/tournament/<id>/schedule`): przegląd rund i stolików (NS/EW).
- **Rundy** — strona „Rundy” (`/tournament/<id>/rounds`): wybór rundy, widoki:
  - **Wyniki** — wpisywanie wyników rozdania: kontrakt (np. 3NT, 4Sx), rozgrywający, wist, liczba lew; walidacja na żywo; zapis punktów NS/EW i IMP (datum).
  - **Ranking** — ranking kumulatywny IMP po wybranych rundach (wymaga zapisanych wyników we wszystkich uwzględnionych rundach); eksport do CSV, drukowanie.
  - **Head-to-head** — macierz IMP drużyna vs drużyna (kumulatywnie do wybranej rundy).

### Ustawienia i API

- **Ustawienia** — `/api/settings`: odczyt i zmiana (np. `debug_mode`).
- **Kontrakt** — `/api/contract-spec`: poziomy, kolory, modyfikatory, wzorzec.
- **Walidacja wyniku** — `/api/validate-result` (POST): sprawdzenie kontraktu i pól, zwrot `ns_score`/`ew_score`.

## Testy

```bash
pytest
```

Testy: `test_contract.py`, `test_round_models.py`, `test_round_results.py`, `test_schedule.py`, `test_scoring.py`, `test_tournament_generator.py`, `test_tournament_rounds.py`, `test_tournament_service.py`, **`test_api_tournaments.py`** (testy API z Flask test client: lista, tworzenie, pobieranie, archiwizacja, zapis wyników rundy, ranking).

## Skrypty demonstracyjne

Z katalogu głównego projektu:

```bash
python -m scripts.run_tournament_demo
python -m scripts.score_random_rounds_demo
python -m scripts.three_cycles_demo
```

- `run_tournament_demo` — generowanie turnieju i rund.
- `score_random_rounds_demo` — losowe wyniki rund.
- `three_cycles_demo` — trzy cykle round-robin dla 6 drużyn, pary i kary za różnicę cykli.

## Struktura projektu

- **`app.py`** — punkt wejścia Flask (konfiguracja `DATA_DIR`, rejestracja blueprintu).
- **`bridge/`** — pakiet główny:
  - **`bridge/api/`** — routes: strona główna, edycja turnieju, rundy, harmonogram, placeholder rankingu; API turniejów, rund, wyników, rankingu, head-to-head, ustawień, contract-spec, walidacja wyniku.
  - **`bridge/models/`** — modele: `contract.py` (kontrakt, walidacja), `round_models.py` (drużyny, rundy, stoliki, rozdania, wyniki), `tournament.py` (turniej, serializacja).
  - **`bridge/storage/`** — zapis/odczyt JSON (katalog `data/`, jeden folder na turniej, brak indeksu; archiwizacja, backup w `archive/`).
  - **`bridge/services/`** — logika: `generator.py` (round-robin, rozdania), `tournament_service.py` (parsowanie payloadu turnieju), `round_results.py` (widok wyników z IMP, ranking kumulatywny, head-to-head).
  - **`bridge/scoring.py`** — liczenie punktów NS/EW z kontraktu i lew, IMP (tabela WBF), IMP na rozdanie (datum).
  - **`bridge/validation.py`** — walidacja wyników (kompletność, kontrakt, rozgrywający, wist, lewy).
- **`tests/`** — testy jednostkowe.
- **`scripts/`** — skrypty demonstracyjne.
- **`templates/`**, **`static/`** — szablony HTML, CSS, JS.
- **`data/`** — zapisane turnieje (JSON w podkatalogach).
- **`docs/`** — dokumentacja: **`API.md`** (opis endpointów API, przykłady JSON), uproszczenia rund, storage.
