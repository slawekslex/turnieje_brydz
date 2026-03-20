# Turniej brydzowy

**Wersja 0.4.0**

Aplikacja webowa (Flask + vanilla JS) do prowadzenia turniejow brydzowych w systemie round-robin: zarzadzanie turniejami, automatyczne generowanie rund i rozdan, wpisywanie wynikow z walidacja, liczenie IMP, ranking kumulatywny i macierz bezposrednich starc.

## Zrzuty ekranu

![Lista turniejow](screenshots/Screenshot%202026-02-06%20143158.png)
![Harmonogram](screenshots/Screenshot%202026-02-06%20143319.png)
![Rundy i wyniki](screenshots/Screenshot%202026-02-06%20143534.png)

## Wymagania

- Python 3.10+

## Instalacja i uruchomienie

1. **Srodowisko wirtualne (zalecane):**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # Linux / macOS
   ```

2. **Instalacja zaleznosci:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Uruchomienie serwera:**

   ```bash
   python app.py
   ```

4. Otworz w przegladarce: **http://127.0.0.1:5000/**

## Konfiguracja (`.env`)

Skopiuj `.env.example` do `.env` i ustaw wartosci. Aplikacja laduje `.env` przy starcie, a zmienne srodowiskowe maja pierwszenstwo.

| Zmienna            | Opis                                    | Domyslnie |
|--------------------|-----------------------------------------|-----------|
| `BRIDGE_DATA_DIR`  | Katalog z danymi turniejow              | `./data`  |
| `FLASK_DEBUG`      | Tryb debug Flask (`true`/`1`/`yes`)     | `false`   |
| `PORT`             | Port serwera                            | `5000`    |
| `FLASK_SECRET_KEY` | Klucz sesji Flask (istotny na produkcji) | —         |

## Funkcjonalnosc

### Turnieje

- **Lista aktywnych turniejow** (`/`) - nazwa i data, z szybkim przejsciem do rund.
- **Tworzenie turnieju** - nazwa, data, druzyny (nazwa + 2 czlonkow), liczba rund, rozdania na runde.
- **Parzysta i nieparzysta liczba druzyn** - dla nieparzystej liczby druzyn system automatycznie dodaje BYE (wolna druzyna).
- **Archiwizacja** - turniej znika z listy aktywnych, dane zostaja w `data/`.
- **Edycja turnieju** (`/tournament/<id>`) - nazwa, data, druzyny, liczba rund, rozdania na runde, liczba boksow.
- **Bezpieczna edycja przy istniejacych wynikach**:
  - zmiany niekrytyczne (np. nazwy) zachowuja wyniki,
  - zmiany krytyczne (np. liczba druzyn, liczba rozdan/runde) wymagaja potwierdzenia i moga wyczyscic wyniki.
- **Walidacja duplikatow nazw druzyn** - API odrzuca turniej z powtorzonymi nazwami.

### Generowanie rund i rozdan

- **Round-robin (circle method)**:
  - parzysta liczba druzyn: `n-1` rund na pelny cykl,
  - nieparzysta liczba druzyn: `n` rund na pelny cykl (1 BYE/runde).
- **Cykle round-robin** - generator potrafi budowac kolejne cykle tak, aby byly mozliwie rozne od poprzednich.
- **Czesciowy ostatni cykl** - gdy liczba rund nie jest wielokrotnoscia rund/cykl.
- **Rozdania na runde** - konfigurowalne (`deals_per_round`).
- **Liczba boksow** (`number_of_boxes`) - dealer i zagrozenia rotuja po sekwencji 16-board i mapuja sie do liczby dostepnych boksow.

### Rundy i wyniki

- **Widok rund** (`/tournament/<id>/rounds`) z szybkim wyborem rundy.
- **Tryb edycji**:
  - wpisywanie `contract`, `declarer`, `opening_lead`, `tricks_taken`,
  - walidacja pojedynczego wiersza przez API (`/api/validate-result`),
  - zapis calej rundy (`/api/tournaments/<id>/round-results`),
  - status zapisu per runda (pelny/czesciowy/blad),
  - skroty i ergonomia: `Ctrl+S`, nawigacja `Tab/Enter`, ostrzezenie o niezapisanych zmianach.
- **Tryb podgladu (po zapisaniu kompletu wynikow)**:
  - **Wyniki rozdan** z IMP na stolik i rozdanie (datum),
  - **Ranking kumulatywny** IMP do wybranej rundy,
  - **Head-to-head** (bezposrednio) - macierz IMP druzyna vs druzyna.
- **Eksport i druk rankingu**:
  - eksport CSV (UTF-8 BOM),
  - drukowanie zestawienia.
- **Pelen harmonogram** (`/tournament/<id>/schedule`) - widok i wydruk NS/EW na kazdy stolik/runde.

### Ustawienia i debug mode

- **Strona ustawien** (`/settings`) dostepna z ikony kola zebatego.
- **`debug_mode`** (`/api/settings`) wlacza przyciski pomocnicze:
  - **Auto** w formularzu turnieju (uzupelnianie testowych druzyn),
  - **Auto** w rundzie (losowe kontrakty i wyniki testowe).

### API (skrot)

Szczegolowa dokumentacja: `docs/API.md`.

- `GET /api/settings`, `PATCH /api/settings`
- `GET /api/tournaments`, `POST /api/tournaments`
- `GET /api/tournaments/<tour_id>`, `PUT /api/tournaments/<tour_id>`
- `POST /api/tournaments/<tour_id>/archive`
- `GET /api/tournaments/<tour_id>/rounds`
- `POST /api/tournaments/<tour_id>/round-results`
- `GET /api/tournaments/<tour_id>/rounds/<round_id>/deal-results`
- `GET /api/tournaments/<tour_id>/rounds/<round_id>/ranking`
- `GET /api/tournaments/<tour_id>/rounds/<round_id>/head-to-head`
- `GET /api/contract-spec`
- `POST /api/validate-result`

## Dane i trwalosc

- Dane sa zapisywane jako JSON w `data/<folder_turnieju>/data.json`.
- Brak centralnego indeksu turniejow - lista budowana przez skan katalogu `data/`.
- Przy kazdym zapisie tworzony jest backup poprzedniej wersji w `data/<folder_turnieju>/archive/`.
- Ustawienia UI (`debug_mode`) sa trzymane w `data/settings.json`.

## Testy

Uruchomienie:

```bash
pytest
```

Zakres testow obejmuje m.in.:

- walidacje kontraktu i punktacji,
- modele rund, dealer/vulnerability i obsluge boksow,
- generator round-robin (parzyste/nieparzyste druzyny, wiele cykli),
- dane wynikow rund, ranking i head-to-head,
- API turniejow (lista, tworzenie, pobieranie, aktualizacja, archiwizacja, zapis wynikow, ranking).

## Skrypty demonstracyjne

Z katalogu glownego projektu:

```bash
python -m scripts.run_tournament_demo
python -m scripts.score_random_rounds_demo
python -m scripts.three_cycles_demo
```

- `run_tournament_demo` - losowy round-robin + przypisanie rozdan.
- `score_random_rounds_demo` - porownanie podobienstwa dwoch cykli.
- `three_cycles_demo` - generowanie trzech cykli i ich kar roznic.

## Struktura projektu

- `app.py` - punkt wejscia Flask i konfiguracja srodowiska.
- `bridge/api/` - routing stron i endpointow REST.
- `bridge/models/` - modele domenowe (turniej, rundy, kontrakt, wyniki).
- `bridge/services/` - logika generatora i agregacji wynikow.
- `bridge/storage/` - trwalosc JSON i ustawienia.
- `bridge/scoring.py` - liczenie punktow i IMP.
- `bridge/validation.py` - walidacja danych wyniku.
- `templates/`, `static/` - warstwa UI.
- `tests/` - testy jednostkowe i API.
- `docs/` - dodatkowa dokumentacja (w tym `API.md`).
