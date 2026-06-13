# Dokumentacja REST API

Serwis Flask (`api/app.py`) udostępnia dane pomiarowe zapisane w PostgreSQL przez
ingestor. Wszystkie endpointy są tylko do odczytu (`GET`) i zwracają dane w
formacie JSON.

- **Bazowy adres:** `http://localhost:5001`
- **Format odpowiedzi:** `application/json`
- **Port:** `5001` (mapowany na hosta w `docker-compose.yml`)

---

## Przegląd endpointów

| Metoda | Ścieżka                                  | Opis                                            |
| ------ | ---------------------------------------- | ----------------------------------------------- |
| GET    | `/health`                                | Status działania API                            |
| GET    | `/`                                      | Prosta strona testowa (`Hello, World!`)         |
| GET    | `/measurements`                          | 20 ostatnich pomiarów ze wszystkich urządzeń    |
| GET    | `/latest`                                | Najnowszy pojedynczy pomiar                      |
| GET    | `/devices`                               | Lista urządzeń mających zapisane pomiary        |
| GET    | `/devices/<device_id>/sensors`           | Lista sensorów dostępnych dla urządzenia        |
| GET    | `/measurements/<device_id>`              | 20 ostatnich pomiarów wybranego urządzenia      |
| GET    | `/measurements/<device_id>/<sensor>`     | 20 ostatnich pomiarów wybranego sensora         |

Wszystkie endpointy zwracające pomiary używają `ORDER BY id DESC` i (poza
`/latest`) `LIMIT 20`.

---

## Szczegóły endpointów

### `GET /health`

Endpoint kontrolny potwierdzający, że aplikacja działa.

```bash
curl http://localhost:5001/health
```

```json
{ "status": "ok" }
```

---

### `GET /measurements`

Zwraca 20 ostatnich pomiarów ze wszystkich urządzeń.

```bash
curl http://localhost:5001/measurements
```

```json
[
  {
    "id": 152,
    "group_id": "g02",
    "device_id": "esp32-15f1ab88",
    "sensor": "temperature",
    "value": 24.5,
    "unit": "C",
    "ts_ms": 1742030400000,
    "seq": 142,
    "topic": "lab/g02/esp32-15f1ab88/temperature",
    "received_at": "2026-06-13T14:00:00Z"
  }
]
```

---

### `GET /latest`

Zwraca najnowszy pojedynczy pomiar (lista z jednym elementem; pusta lista, gdy
brak danych).

```bash
curl http://localhost:5001/latest
```

```json
[
  {
    "id": 152,
    "group_id": "g02",
    "device_id": "esp32-15f1ab88",
    "sensor": "temperature",
    "value": 24.5,
    "unit": "C",
    "ts_ms": 1742030400000,
    "seq": 142,
    "topic": "lab/g02/esp32-15f1ab88/temperature",
    "received_at": "2026-06-13T14:00:00Z"
  }
]
```

---

### `GET /devices`

Zwraca listę unikalnych urządzeń, które mają zapisane pomiary.

```bash
curl http://localhost:5001/devices
```

```json
[
  { "device_id": "esp32-15f1ab88" },
  { "device_id": "esp32-test" }
]
```

---

### `GET /devices/<device_id>/sensors`

Zwraca listę unikalnych typów sensorów dostępnych dla wskazanego urządzenia.

```bash
curl http://localhost:5001/devices/esp32-15f1ab88/sensors
```

```json
[
  { "sensor": "pressure" },
  { "sensor": "temperature" }
]
```

---

### `GET /measurements/<device_id>`

Zwraca 20 ostatnich pomiarów wybranego urządzenia (wszystkie sensory).

```bash
curl http://localhost:5001/measurements/esp32-15f1ab88
```

Struktura rekordów jak w `/measurements`, filtrowana po `device_id`.

---

### `GET /measurements/<device_id>/<sensor>`

Zwraca 20 ostatnich pomiarów wybranego sensora danego urządzenia. Endpoint
wykorzystywany przez GUI (`ui/`) do odświeżania wykresu.

```bash
curl http://localhost:5001/measurements/esp32-15f1ab88/temperature
```

Struktura rekordów jak w `/measurements`, filtrowana po `device_id` i `sensor`.

---

## Pola w odpowiedzi (rekord pomiaru)

| Pole          | Typ     | Opis                                                  |
| ------------- | ------- | ----------------------------------------------------- |
| `id`          | integer | Identyfikator rekordu (klucz główny)                  |
| `group_id`    | string  | Identyfikator grupy laboratoryjnej                    |
| `device_id`   | string  | Identyfikator urządzenia                              |
| `sensor`      | string  | Typ pomiaru (`temperature`, `pressure`)               |
| `value`       | number  | Zmierzona wartość                                     |
| `unit`        | string  | Jednostka (`C`, `hPa`)                                |
| `ts_ms`       | integer | Znacznik czasu pomiaru (Unix epoch w ms)             |
| `seq`         | integer | Numer sekwencyjny wiadomości                          |
| `topic`       | string  | Topic MQTT, z którego pochodzi rekord                 |
| `received_at` | string  | Czas odbioru przez backend (ISO 8601, UTC)            |

---

## Kody odpowiedzi

- `200 OK` — poprawna odpowiedź (również pusta lista `[]`, gdy brak danych).
- `404 Not Found` — nieznana ścieżka.
- `500 Internal Server Error` — błąd po stronie serwera (np. brak połączenia z bazą).

---

## Testowanie

### Przeglądarka
```
http://localhost:5001/health
http://localhost:5001/measurements
http://localhost:5001/devices
```

### curl
```bash
curl http://localhost:5001/health
curl http://localhost:5001/measurements
curl http://localhost:5001/latest
curl http://localhost:5001/devices
curl http://localhost:5001/devices/esp32-15f1ab88/sensors
curl http://localhost:5001/measurements/esp32-15f1ab88/temperature
```

---

## Uwagi

- Konfiguracja połączenia z bazą jest wydzielona do `api/db.py` i pobierana ze
  zmiennych środowiskowych (`api/.env`).
- Endpointy filtrujące są realizowane jako ścieżki (`/measurements/<device_id>`,
  `/measurements/<device_id>/<sensor>`) zamiast `/measurements/history` z
  parametrami query — pokrywa to filtrowanie po urządzeniu i sensorze.
