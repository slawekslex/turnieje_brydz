# Turniej brydżowy

Aplikacja do zarządzania turniejami brydżowymi: lista turniejów oraz tworzenie nowych (metadane + drużyny). Harmonogram rund i rozdania generowane są automatycznie.

## Wymagania

- Python 3.10+

## Uruchomienie

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

## Użycie

- **Lista turniejów** — na stronie głównej widoczna jest lista zapisanych turniejów (nazwa, data).
- **Dodaj turniej** — przycisk „Dodaj turniej” otwiera formularz:
  - nazwa turnieju,
  - data,
  - drużyny: dla każdej drużyny podaj nazwę oraz dwóch członków.
  Liczba drużyn musi być parzysta (minimum 2). Przycisk „+ Drużyna” dodaje kolejną drużynę.

Po zapisaniu turnieju generowany jest harmonogram rund (round-robin) oraz rozdania; dane zapisywane są w katalogu `data/`.

## Testy

```bash
pytest
```

## Skrypty demonstracyjne

Z katalogu głównego projektu:

```bash
python -m scripts.run_tournament_demo
python -m scripts.score_random_rounds_demo
```

## Struktura projektu

- **`app.py`** — punkt wejścia aplikacji Flask (rejestracja blueprintu, konfiguracja)
- **`bridge/`** — pakiet główny:
  - **`bridge/api/`** — endpointy (Flask routes: lista turniejów, tworzenie turnieju, strona główna)
  - **`bridge/models/`** — modele danych: drużyny, rundy, rozdania, turniej + serializacja do słownika
  - **`bridge/storage/`** — zapis/odczyt plików JSON (turnieje, indeks)
  - **`bridge/services/`** — logika biznesowa: generowanie harmonogramu rund (round-robin), walidacja
- **`tests/`** — testy jednostkowe (`test_round_models.py`, `test_tournament_generator.py`)
- **`scripts/`** — skrypty demonstracyjne (`run_tournament_demo.py`, `score_random_rounds_demo.py`)
- **`templates/`**, **`static/`** — szablony HTML, CSS, JS
- **`data/`** — zapisane turnieje (JSON)
