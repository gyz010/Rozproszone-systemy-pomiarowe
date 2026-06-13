# Rozproszone systemy pomiarowe

Repozytorium startowe do projektu z systemów rozproszonych.  
Projekt dotyczy budowy rozproszonego systemu pomiarowego, w którym urządzenia ESP32 zbierają dane z czujników, publikują je do brokera MQTT, a następnie dane są odbierane przez serwisy backendowe, zapisywane do bazy danych i udostępniane przez REST API.

Aktualna wersja obsługuje czujnik BMP280 na ESP32. Urządzenie publikuje dwa typy pomiarów:
- `temperature` w jednostce `C`
- `pressure` w jednostce `hPa`

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

ESP32 łączy się z brokerem po MQTT przez TLS na porcie `8883`. W pliku `esp32/include/secrets.h` ustaw:

```cpp
#define MQTT_HOST "<IP hosta Windows w sieci LAN>"
#define MQTT_PORT 8883
#define MQTT_TLS_CN "broker"
#define MQTT_GROUP "g02"
```

Jeżeli Docker działa w WSL, ruch z ESP32 do brokera przechodzi przez Windows portproxy:

```powershell
netsh interface portproxy add v4tov4 listenport=8883 listenaddress=0.0.0.0 connectport=8883 connectaddress=<WSL_IP>
netsh advfirewall firewall add rule name="MQTT TLS 8883" dir=in action=allow protocol=TCP localport=8883
```

Adres WSL można sprawdzić poleceniem:

```bash
wsl hostname -I
```

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

### REST API

API udostępnia między innymi:

- `GET /health` — status API
- `GET /devices` — lista urządzeń, które mają zapisane pomiary
- `GET /devices/<device_id>/sensors` — lista sensorów dostępnych dla urządzenia
- `GET /measurements` — ostatnie pomiary ze wszystkich urządzeń
- `GET /latest` — najnowszy pojedynczy pomiar
- `GET /measurements/<device_id>` — ostatnie pomiary wybranego urządzenia
- `GET /measurements/<device_id>/<sensor>` — ostatnie pomiary wybranego sensora urządzenia

Pełna dokumentacja endpointów znajduje się w `docs/api.md`.

### Aplikacja GUI

Interfejs w `ui/gui.py` łączy się z REST API, pobiera listę urządzeń i dostępnych sensorów, a następnie odświeża wykres wybranego sensora cyklicznie. Wykres obsługuje dane z API dla `temperature` i `pressure`; lista sensorów jest pobierana z bazy, więc GUI pokazuje tylko faktycznie zapisane typy pomiarów.

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