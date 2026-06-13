# Dokumentacja Ingestora MQTT

## 1. Cel serwisu

Serwis **ingestor** jest kluczowym komponentem systemu rozproszonego. Jego zadaniem jest:

- **Subskrybowanie topicu MQTT** `lab/+/+/+` (wszelkich wiadomości z urządzeń pomiarowych)
- **Parsowanie payloadu JSON** przychodzących wiadomości
- **Walidacja danych** – sprawdzenie obecności i typów pól wymaganych (`device_id`, `sensor`, `value`, `ts_ms`) zgodnie z `docs/message_contract.md`
- **Uzupełnianie `group_id`** – gdy brak w JSON, wartość jest wyciągana z topicu `lab/<group_id>/<device_id>/<sensor>`
- **Zapis do bazy danych** – poprawne wiadomości zapisywane są w tabeli `measurements` bazy PostgreSQL
- **Obsługa błędów** – wiadomości niezgodne ze schematem są rejestrowane w logach i odrzucane

---

## 2. Sposób uruchomienia

### Uruchomienie całego środowiska

Aby uruchomić system (w tym ingestor, broker MQTT, bazę danych i API), użyj Docker Compose:

```bash
docker compose up -d --build
```

Flagi:

- `-d` – uruchomienie w tle (detached mode)
- `--build` – przebudowanie obrazów Docker

### Sprawdzenie statusu kontenerów

```bash
docker compose ps
```

Spodziewane kontenery:

- `api` (serwis Flask na porcie 5001)
- `broker` (serwis MQTT Mosquitto na porcie 8883 z TLS)
- `postgres` (baza danych PostgreSQL na porcie 5432)
- `ingestor` (serwis ingestora – brak mapowania portów)

### Zatrzymanie środowiska

```bash
docker compose down
```

---

## 3. Sposób testowania

### 3.1. Sprawdzenie logów ingestora

Aby obserwować logi w czasie rzeczywistym:

```bash
docker compose logs -f ingestor
```

Spodziewane logi:

- `Połączono z brokerem MQTT przez TLS (kod: 0)` – pomyślne połączenie
- `Poprawnie zapisano wiadomość z: lab/...` – pomyślny zapis do bazy
- `Niepoprawny format danych: ...` – wiadomość odrzucona z powodu walidacji
- `Błąd przetwarzania wiadomości: ...` – błąd parsowania lub przetwarzania

### 3.2. Połączenie z bazą danych i weryfikacja danych

Aby sprawdzić zapis pomiarów w bazie, użyj klienta PostgreSQL:

```bash
docker compose exec postgres psql -U admin -d abcd_db
```

W otwartym shellu PostgreSQL wykonaj zapytanie:

```sql
SELECT * FROM measurements ORDER BY id DESC LIMIT 10;
```

Spodziewane kolumny:

- `id` – identyfikator rekordu
- `group_id` – identyfikator grupy (np. `gr1`)
- `device_id` – identyfikator urządzenia (np. `esp32-abc12345`)
- `sensor` – typ pomiaru (np. `temperature` albo `pressure`)
- `value` – zmierzona wartość (np. `24.5`)
- `unit` – jednostka (np. `C` albo `hPa`)
- `ts_ms` – timestamp w ms (liczba całkowita)
- `seq` – numer sekwencyjny
- `topic` – topic MQTT, na którym przyszła wiadomość (np. `lab/gr1/esp32-abc12345/temperature`)
- `received_at` – znacznik czasu odboru w bazie (timestamp)

Aby wyjść z shellu PostgreSQL:

```
\q
```

## 4. Przykłady wiadomości (Payload JSON)

### 4.1. Poprawna wiadomość

**Topic:** `lab/g02/esp32-abc12345/temperature`

**Payload:**

```json
{
  "device_id": "esp32-abc12345",
  "sensor": "temperature",
  "value": 24.5,
  "ts_ms": 1710928373000,
  "unit": "C",
  "schema_version": 1,
  "seq": 142
}
```

**Rezultat:** Wiadomość zostanie zapisana do tabeli `measurements`. W logach ingestora pojawi się:

```
Poprawnie zapisano wiadomość z: lab/g02/esp32-abc12345/temperature
```

### 4.2. Poprawna wiadomość bez `group_id` w JSON

**Topic:** `lab/g02/esp32-abc12345/temperature`

**Payload:**

```json
{
  "device_id": "esp32-abc12345",
  "sensor": "temperature",
  "value": 24.5,
  "ts_ms": 1710928373000,
  "unit": "C",
  "seq": 142
}
```

**Rezultat:** Ingestor uzupełni `group_id` wartością `g02` na podstawie topicu i zapisze rekord do bazy.

### 4.3. Poprawna wiadomość z ciśnieniem

**Topic:** `lab/g02/esp32-abc12345/pressure`

**Payload:**

```json
{
  "group_id": "gr1",
  "device_id": "esp32-abc12345",
  "sensor": "pressure",
  "value": 1008.4,
  "ts_ms": 1710928373000,
  "unit": "hPa",
  "seq": 143
}
```

### 4.4. Błędna wiadomość – brakujące pole `ts_ms`

**Topic:** `lab/gr1/esp32-test/temperature`

**Payload:**

```json
{
  "device_id": "esp32-test",
  "sensor": "temperature",
  "value": 21.3,
  "unit": "C"
}
```

**Rezultat:** Wiadomość zostanie **odrzucona** ze względu na brakujące pole `ts_ms` (wymagane). W logach ingestora pojawi się:

```
Niepoprawny format danych: {'device_id': 'esp32-test', 'sensor': 'temperature', 'value': 21.3, 'unit': 'C'}
```

**Wiadomość NIE będzie zapisana w bazie danych.**

### 4.5. Błędna wiadomość – `value` jako string

**Topic:** `lab/gr1/esp32-test/temperature`

**Payload:**

```json
{
  "device_id": "esp32-test",
  "sensor": "temperature",
  "value": "23.5",
  "ts_ms": 1710928373000
}
```

**Rezultat:** Wiadomość zostanie **odrzucona** na etapie walidacji typów (`value` musi być liczbą, nie stringiem). W logach:

```
Niepoprawny format danych: {'device_id': 'esp32-test', 'sensor': 'temperature', 'value': '23.5', 'ts_ms': 1710928373000}
```

**Wiadomość NIE będzie zapisana w bazie danych.**

---

## 5. Struktura tabeli `measurements`

Definicja tabeli w bazie danych:

```sql
CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL PRIMARY KEY,
    group_id TEXT,
    device_id TEXT NOT NULL,
    sensor TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    ts_ms BIGINT NOT NULL,
    seq INTEGER,
    topic TEXT,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Wymagane pola i reguły walidacji

Zgodnie z kontraktem komunikacyjnym systemu, każda wiadomość **musi zawierać**:

| Pole        | Typ     | Opis                                               |
| ----------- | ------- | -------------------------------------------------- |
| `device_id` | string  | Identyfikator urządzenia (np. `esp32-abc12345`)    |
| `sensor`    | string  | Typ pomiaru (np. `temperature` lub `pressure`)     |
| `value`     | number  | Zmierzona wartość (musi być liczbą, nie stringiem) |
| `ts_ms`     | integer | Timestamp w millisekundach epoki UNIX (`> 0`)        |

Reguły walidacji w ingestorze:

1. `device_id` i `sensor` muszą być niepustymi stringami.
2. `value` musi być liczbą (`int` lub `float`), nie stringiem ani `bool`.
3. `ts_ms` musi być dodatnią liczbą całkowitą.
4. `seq`, jeśli występuje, musi być liczbą całkowitą `>= 0`.
5. `unit`, jeśli występuje, musi pasować do sensora (`temperature` → `C`, `pressure` → `hPa`).
6. `group_id` może być w JSON lub zostanie pobrane z topicu `lab/<group_id>/...`.

Pola opcjonalne:

- `unit` – jednostka pomiarowa (`C` albo `hPa`)
- `seq` – numer sekwencyjny wiadomości
- `schema_version` – wersja schematu
- `group_id` – identyfikator grupy (opcjonalne w JSON, jeśli jest w topicu)
