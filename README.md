# Rozproszone systemy pomiarowe

Repozytorium startowe do projektu z systemów rozproszonych.  
Projekt dotyczy budowy rozproszonego systemu pomiarowego, w którym urządzenia ESP32 zbierają dane z czujników, publikują je do brokera MQTT, a następnie dane są odbierane przez serwisy backendowe, zapisywane do bazy danych i udostępniane przez REST API.

Aktualnie projekt zawiera przygotowane serwisy backendowe uruchamiane przez Docker Compose oraz katalogi na kolejne elementy systemu, takie jak:
- `esp32`
- `ingestor`
- `ui`
- `docs`

---

## Quick Start

Poniższa instrukcja pozwala uruchomić podstawową wersję środowiska projektowego dla systemu rozproszonego.

### Wymagania

Przed uruchomieniem upewnij się, że masz zainstalowane:
- Docker
- Docker Compose

### Klonowanie repozytorium

```bash
git clone https://github.com/mateuszbartczak-pwr/Rozproszone-systemy-pomiarowe.git
cd Rozproszone-systemy-pomiarowe
```

### Certyfikaty TLS (MQTT)

Przed pierwszym uruchomieniem wygeneruj certyfikaty brokera (WSL/Linux):

```bash
cd broker/certs
chmod +x generate-certs.sh
./generate-certs.sh
cp ca.crt ../../ingestor/certs/
```

Następnie zaktualizuj `esp32/include/ca_cert.h` zawartością `broker/certs/ca.crt` (jeśli generujesz certyfikaty ponownie).

### Uruchomienie środowiska
Aby zbudować i uruchomić wszystkie dostępne serwisy (z WSL):

```bash
docker compose up --build
```
lub aby uruchomić środowisko w tle:
```bash
docker compose up -d --build
```
### Zatrzymanie środowiska
```bash
docker compose down
```

### Aktualnie dostępne serwisy

Po uruchomieniu Docker Compose powinny być dostępne następujące usługi:

- REST API (Flask) — http://localhost:5001

- Broker MQTT (TLS) — localhost:8883

- PostgreSQL — dostępna tylko w sieci Docker `backend` (bez mapowania portu na hosta)

### Podgląd logów

Aby sprawdzić logi wszystkich serwisów:
```bash
docker compose logs
```

Aby śledzić logi na żywo:
```bash
docker compose logs -f
```

Aby wyświetlić logi tylko jednego serwisu:
```bash
docker compose logs -f flask
docker compose logs -f broker
docker compose logs -f database
```
Sprawdzenie statusu kontenerów
```bash
docker compose ps
```

### Struktura projektu

Repozytorium zawiera między innymi następujące katalogi:

- `api/` — backend REST API

- `broker/` — broker MQTT

- `database/` — baza danych PostgreSQL

- `esp32/` — kod dla urządzeń ESP32

- `ingestor/` — serwis odbierający dane z MQTT i zapisujący je do bazy

- `ui/` — warstwa interfejsu użytkownika

- `docs/` — dokumentacja projektu

- `utils/` — narzędzia pomocnicze

### Uwagi

Projekt będzie rozwijany etapami w trakcie semestru.
W kolejnych zajęciach repozytorium będzie rozszerzane o dodatkowe serwisy, integracje i mechanizmy bezpieczeństwa.