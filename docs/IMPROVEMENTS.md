# Sugestie ulepszeń aplikacji Turniej brydżowy

Propozycje ulepszeń w trzech obszarach: **funkcjonalność**, **jakość kodu** i **użyteczność**.

**Zaimplementowane:** 1.6 (duplikaty nazw drużyn), 1.7 (skróty klawiaturowe), 2.1 (polskie komunikaty), 2.2 (redirect rankingu), 2.3 (obsługa błędów load_tournament), 2.4 (schedule_view_data), 2.5 (require tournament/round), 2.6 (config z env + .env), 2.7 (testy API), 3.2 (feedback po zapisie), 3.3 (breadcrumbs), 3.8 (docs/API.md).

---

## 1. Funkcjonalność

### 1.1 Archiwum turniejów
- **Problem:** Zarchiwizowane turnieje znikają z listy bez możliwości ich zobaczenia ani przywrócenia.
- **Propozycja:** Na stronie głównej dodać przełącznik „Pokaż zarchiwizowane” lub link „Archiwum”, lista z `archived=true`. Dla każdego zarchiwizowanego turnieju przycisk „Przywróć” (zapis z `archived=False`).

### 1.2 Potwierdzenie przed archiwizacją
- **Problem:** Kliknięcie „Archiwizuj” od razu usuwa turniej z listy; łatwo o pomyłkę.
- **Propozycja:** Modal lub `confirm()`: „Czy na pewno chcesz zarchiwizować turniej X? Będzie go można przywrócić z archiwum.”

### 1.3 Ranking całego turnieju
- **Problem:** Ranking IMP jest tylko „po rundzie N” (kumulatywnie do N). Brak jednego widoku „końcowy ranking turnieju”.
- **Propozycja:** Strona lub zakładka „Ranking turnieju” z sumą IMP po ostatniej rundzie (wykorzystać istniejące API z `round_id` ostatniej rundy). Ewentualnie endpoint `GET /api/tournaments/<id>/final-ranking`.

### 1.4 Eksport / backup danych
- **Problem:** Jedyna „kopia” to pliki w `data/` i automatyczne kopie w `archive/`.
- **Propozycja:** Przycisk „Pobierz backup” (np. na stronie turnieju lub w ustawieniach): jeden plik ZIP lub JSON z wybranym turniejem lub całą zawartością `data/`, żeby użytkownik mógł trzymać kopię poza serwerem.

### 1.5 Walidacja wistu (opening lead)
- **Problem:** Pole „wist” jest wymagane, ale przyjmuje dowolny tekst; nie ma sprawdzenia formatu (np. karta: 2C, 10H, AS).
- **Propozycja:** Opcjonalna walidacja formatu: np. rozpoznawanie kart (2–9, T/10, J, Q, K, A + kolor C/D/H/S). Komunikat typu: „Wpisz kartę, np. 2C, AS, 10H”.

### 1.6 Ostrzeżenie o duplikatach nazw drużyn — ✅ Zaimplementowano
- Walidacja w `parse_tournament_payload`: przy duplikatach nazw zwracany błąd po polsku; zapis blokowany.

### 1.7 Skróty klawiaturowe — ✅ Zaimplementowano
- Tab / Enter: następne/poprzednie pole i wiersz. Ctrl+S / Cmd+S: zapis rundy. Podpowiedź „Ctrl+S” przy przycisku Zapisz.

---

## 2. Jakość kodu

### 2.1 Spójna język komunikatów (i18n) — ✅ Zaimplementowano
- Komunikaty API i walidacji po polsku (tournament_service, routes, round_results).

### 2.2 Usunięcie martwego kodu (ranking placeholder) — ✅ Zaimplementowano
- Route `/tournament/…/rounds/…/ranking` przekierowuje do strony rund z `?round=X&view=standings`.

### 2.3 Obsługa błędów przy ładowaniu turnieju — ✅ Zaimplementowano
- Helper `_get_tournament_or_error`, szablon 503, logowanie; 404/503 zamiast 500.

### 2.4 Wydzielenie logiki harmonogramu z routes — ✅ Zaimplementowano
- `bridge.services.schedule.schedule_view_data(tournament)`; testy w `test_schedule.py`.

### 2.5 Wspólny wzorzec „znajdź turniej / rundę” — ✅ Zaimplementowano
- `_require_tournament_path`, `_get_round_or_error`; route’y zrefaktoryzowane.

### 2.6 Konfiguracja z zmiennych środowiskowych — ✅ Zaimplementowano
- BRIDGE_DATA_DIR, FLASK_DEBUG, PORT, FLASK_SECRET_KEY; ładowanie z `.env` (python-dotenv), `.env.example`.

### 2.7 Testy API i integracyjne — ✅ Zaimplementowano
- `tests/test_api_tournaments.py` (Flask test client): lista, create, get, archive, round-results, ranking, walidacja.

### 2.8 Typowanie i walidacja payloadów
- **Problem:** Payloady JSON są parsowane ręcznie (`.get()`, rzutowania); łatwo o błędy przy zmianie API.
- **Propozycja:** Rozważyć Pydantic (lub dataclasses) dla request body (np. create tournament, save round results): walidacja i typy w jednym miejscu, czytelniejsze błędy 400.

---

## 3. Użyteczność (UX / DX)

### 3.1 Wskaźniki ładowania
- **Problem:** Przy wolnych requestach (duży turniej, wiele rund) użytkownik nie wie, czy strona się ładuje, czy zawiesiła.
- **Propozycja:** Spinner lub „Ładowanie…” przy listach (turnieje, rundy) i przy zapisie wyników; wyłączyć przycisk „Zapisz” na czas żądania (przycisk jest już wyłączany podczas zapisu).

### 3.2 Jednoznaczny feedback po zapisie — ✅ Zaimplementowano
- Komunikaty: „Zapisano X z Y wyników.”, przy błędach: liczba wierszy z błędami + „popraw je i zapisz ponownie.”; wiersze z błędami podświetlone.

### 3.3 Breadcrumbs — ✅ Zaimplementowano
- Lista turniejów > [Nazwa] > Edycja/Rundy/Harmonogram na stronach turnieju; nazwa uzupełniana z API.

### 3.4 Podpowiedź formatu kontraktu
- **Problem:** Nie wszyscy pamiętają format (3NT, 4Sx); pole może być puste bez wskazówki.
- **Propozycja:** Placeholder lub mały tekst pod polem: „np. 3NT, 4Sx, 6Hxx” (spójnie z komunikatem błędu w walidacji).

### 3.5 Widok „pustej” rundy
- **Problem:** Gdy w turnieju nie ma jeszcze rund (teoretycznie) lub brak wyników, warto to wyraźnie pokazać.
- **Propozycja:** Krótki komunikat w widoku Wyniki: „Brak zapisanych wyników. Wypełnij pola poniżej i zapisz.” zamiast pustej tabeli bez kontekstu.

### 3.6 Dostępność (a11y)
- **Problem:** Modal ustawień i duże tabele mogą być słabo obsługiwane przez czytniki ekranu i nawigację klawiaturową.
- **Propozycja:** Upewnić się, że focus jest uwięziony w modalu i wraca po zamknięciu; `aria-live` dla dynamicznie ładowanego rankingu; nagłówki tabel z `<th scope="col">`; kontrast i rozmiary przycisków zgodne z WCAG.

### 3.7 Responsywność na mobile
- **Problem:** Tabele z wieloma kolumnami (wyniki, ranking) na wąskim ekranie mogą być nieczytelne.
- **Propozycja:** Na małych ekranach: przewijanie poziome z wyraźnym wskaźnikiem, ewentualnie uproszczony widok (np. tylko suma IMP w rankingu); większe pola dotykowe dla przycisków.

### 3.8 Dokumentacja API (dla deweloperów) — ✅ Zaimplementowano
- `docs/API.md`: endpointy, metody, parametry, przykłady JSON (create, round-results, validate-result itd.).

---

## Priorytetyzacja (propozycja)

| Priorytet | Działanie |
|-----------|-----------|
| **Wysoki** | 1.2 (potwierdzenie archiwizacji), 3.1 (wskaźniki ładowania) |
| **Średni** | 1.1 (archiwum + przywracanie), 3.4 (placeholder kontraktu), 3.5 (pusty widok rundy) |
| **Niższy** | 1.3 (ranking turnieju), 1.4 (backup), 1.5 (walidacja wistu), 2.8 (Pydantic), 3.6 (a11y), 3.7 (mobile) |

Można realizować po jednym punkcie z wybranej kategorii i testować od razu w działającej aplikacji.

---

## Drugi przegląd – dodatkowe sugestie

- **Wersjonowanie API:** Przy ewentualnych zmianach kontraktu (np. nowe pola w JSON) rozważyć prefix wersji w URL (`/api/v1/...`) lub nagłówek `Accept` z wersją, żeby nie łamać istniejących klientów.
- **Limit rozmiaru requestu:** Ograniczenie rozmiaru body (np. `app.config['MAX_CONTENT_LENGTH']`) chroni przed nadmiernie dużymi payloadami przy zapisie wielu wyników.
- **CORS:** Jeśli API ma być używane z innej domeny (SPA, mobilka), dodać konfigurację CORS (np. `flask-cors`).
- **Health check:** Endpoint `GET /api/health` lub `/ping` zwracający 200, przydatny przy wdrożeniu (load balancer, kontenery).
- **Import wyników:** Opcjonalnie: wczytywanie wyników z pliku (CSV/JSON) zamiast ręcznego wpisywania przy dużej liczbie rozdań.
