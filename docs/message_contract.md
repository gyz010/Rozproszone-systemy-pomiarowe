# Message Contract

Dokument opisuje kontrakt komunikacyjny dla urządzeń (np. mikrokontrolerów ESP32) przekazujących dane w ramach realizowanego systemu rozproszonego, zgodnie z przyjętymi instrukcjami laboratoryjnymi.

## 1. Struktura Topiców MQTT

Zgodnie w ogólnodostępnymi wymaganiami, dane z czujników i statusy wysyłane są na odpowiednio zdefiniowane i sformalizowane topici.

### Hierarchia:

- **Topic dla danych pomiarowych:** `lab/<group_id>/<device_id>/<sensor>`
- **Topic dla statusu urządzenia:** `lab/<group_id>/<device_id>/status`

Przykładowa wiadomość dla statusu urządzenia:

```json
{
  "schema_version": 1,
  "device_id": "esp32-ab12cd34",
  "status": "online",
  "ts_ms": 1742030400000
}
```

### Zasady nazewnictwa:

- Należy używać **tylko małych liter**.
- Brak znaków spacji.
- Brak polskich znaków.
- Zachowujemy stałą kolejność segmentów.
- Nie umieszczamy wartości pomiarowej w nazwie topicu.
- Topic powinien opisywać klasę komunikatu, a nie pojedynczą próbkę.

_Na podstawie aktualnego formatu w `esp32/src/main.cpp`:_

- `group_id`: Konfigurowalne za pomocą makra `MQTT_GROUP` (np. `gr1`).
- `device_id`: Generowane automatycznie na podstawie adresu MAC z prefiksem np. `esp32-1A2B3C4D`.
- `sensor`: W kodzie urządzenia nazwano to `temperature` pisane w małych literach.

Ostateczny przykładowy topic publikacji:
`lab/gr1/esp32-15f1ab88/temperature`

---

## 2. Format wiadomości JSON (v1)

Każda przesyłana wiadomość telemetryczna zawarta w payloadzie MQTT jest zdefiniowanym słownikiem JSON.

### Pola Wymagane

| Pole        | Typ     | Opis                                                                                                   |
| ----------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `device_id` | string  | Unikalny identyfikator urządzenia klienta. Zgodnie z kodem ESP jest to prefiks "esp32" + hex chip_id.  |
| `sensor`    | string  | Określenie rodzaju sensora obsługującego pomiar. Zgodnie z kodem ESP w tym projekcie: `"temperature"`. |
| `value`     | number  | Zmierzona wielkość fizyczna (np. `24.5`). Uwaga: float lub integer, ale musi być typem liczbowym.      |
| `ts_ms`     | integer | Znacznik czasu z wygenerowania danych w standardzie _Unix epoch_ w milisekundach.                      |

### Pola Opcjonalne

| Pole             | Typ     | Opis                                                                                                        |
| ---------------- | ------- | ----------------------------------------------------------------------------------------------------------- |
| `schema_version` | integer | Oznacza wersję zastosowanego kontraktu dla schematu. Powinna wynosić `1`.                                   |
| `group_id`       | string  | Identyfikator przydzielonej grupy w ramach labolatorium.                                                    |
| `unit`           | string  | Znacznik jednostki pomiarowej wygenerowanej wartości `value`. Zgodnie z kodem mikrokontrolera ESP to `"C"`. |
| `seq`            | integer | Sekwencyjny numer wiadomości pozwalający kontrolować czy pakiety uległy zagubieniu lub zduplikowaniu.       |

---

## 3. Reguły walidacji

Dane przed wczytaniem na magazyn (backend) powinny podlegać ścisłej weryfikacji zgodnie z listą zasad, niezależnie jaki język bazowy realizuje weryfikację.

1. Pole `device_id` **musi być niepustym napisem**.
2. Pole `sensor` **musi być napisem**.
3. Pole `value` **musi być liczbą**. Próba parsowania stringów (np. `"24.5"`), uznawana powinna być za naruszenie formatu.
4. Pole `ts_ms` **musi być dodatnią liczbą całkowitą**. Format musi bazować na ms w epoce UNIX.
5. Pole `unit`, jeśli występuje, **musi odpowiadać typowi sensora**.
6. Pole `seq`, jeśli występuje, **musi być liczbą całkowitą nieujemną** (`>= 0`).

---

## 4. Przykłady wiadomości (v1)

### Poprawna wiadomość wywodząca się z ESP32

Zgodna struktura z polem wymaganym oraz załączonymi opcjonalnymi (np. dodanie `schema_version` oraz `seq` czy jednostką `unit="C"` wykorzystywaną na płycie testowej).

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

### Błędna wiadomość: `value` zapisane jako string

Poniższa wiadomość zostanie odrzucona przez walidator po stronie backendu na wzgląd na obecność pola `value` jako typu string.

```json
{
  "device_id": "esp32-abc12345",
  "sensor": "temperature",
  "value": "24.5",
  "ts_ms": 1710928373000
}
```

### Błędna wiadomość: Brak znacznika czasu i pusty device id

Złamanie dwóch zasad w jednym pakiecie: puste, niereprezentatywne pola znakowe `device_id` i całkowity brak wymaganego timestampa ms `ts_ms`.

```json
{
  "device_id": "",
  "sensor": "temperature",
  "value": 24.5,
  "unit": "C"
}
```

### Błędna wiadomość: Ujemny seq i ts_ms

Pola sekwencji czy unix epoch nie mogą przyjmować wartości z minusem u podstaw.

```json
{
  "device_id": "esp32-abcdfffe",
  "sensor": "temperature",
  "value": 21.0,
  "ts_ms": -1710928373000,
  "seq": -5
}
```
