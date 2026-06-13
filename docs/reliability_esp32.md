# Niezawodność po stronie ESP32 (reconnect, status, Last Will)

Dokument opisuje mechanizmy niezawodności zaimplementowane w firmware ESP32
(`esp32/src/main.cpp`): wykrywanie i ponowne nawiązywanie połączenia Wi-Fi oraz
MQTT, osobny topic statusowy i komunikat Last Will and Testament (LWT).

---

## 1. Topic statusowy

Dane techniczne urządzenia są publikowane na osobnym topicu, oddzielonym od danych
pomiarowych:

```
lab/<group_id>/<device_id>/status
```

Przykład: `lab/g02/esp32-15f1ab88/status`

Topic jest budowany w `setup()`:

```cpp
statusTopic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/status";
```

### Payload statusowy

Komunikat `online` (publikowany z flagą retained po poprawnym połączeniu):

```json
{
  "group_id": "g02",
  "device_id": "esp32-15f1ab88",
  "status": "online",
  "ts_ms": 1742030400000
}
```

Komunikat `offline` (Last Will, publikowany przez brokera przy niepoprawnym
rozłączeniu klienta):

```json
{
  "group_id": "g02",
  "device_id": "esp32-15f1ab88",
  "status": "offline"
}
```

Uwaga: pole `ts_ms` w komunikacie `online` jest dodawane tylko wtedy, gdy czas
został wcześniej zsynchronizowany przez NTP. W payloadzie LWT nie ma `ts_ms`,
ponieważ jest on przygotowywany z góry przez klienta i publikowany dopiero przez
brokera w nieokreślonym momencie awarii.

---

## 2. Reconnect Wi-Fi

Funkcja `connectWiFiIfNeeded()` jest wywoływana cyklicznie w `loop()` i:

- sprawdza stan połączenia przez `WiFi.status()`,
- nie wywołuje `WiFi.begin()` częściej niż co `WIFI_RETRY_MS` (5000 ms),
- nie blokuje pętli głównej (brak pętli `while` z `delay`),
- raportuje stan przez `Serial`,
- po utracie Wi-Fi unieważnia stan synchronizacji NTP, aby po powrocie sieci
  czas został zsynchronizowany ponownie.

```cpp
void connectWiFiIfNeeded() {
    if (WiFi.status() == WL_CONNECTED) return;
    if (millis() - lastWifiAttemptMs < WIFI_RETRY_MS) return;
    lastWifiAttemptMs = millis();
    ntpSynced = false;
    ntpConfigSent = false;
    Serial.println("WiFi disconnected. Trying reconnect...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}
```

---

## 3. Reconnect MQTT

Funkcja `connectMqttIfNeeded()`:

- działa tylko wtedy, gdy Wi-Fi jest aktywne (`WiFi.status() == WL_CONNECTED`),
- cyklicznie sprawdza `mqttClient.connected()`,
- podejmuje próby połączenia nie częściej niż co `MQTT_RETRY_MS` (3000 ms),
- nawiązuje połączenie TLS (`WiFiClientSecure` z certyfikatem CA),
- konfiguruje Last Will przy połączeniu,
- po poprawnym połączeniu natychmiast publikuje status `online`.

Reconnect Wi-Fi i reconnect MQTT są celowo rozdzielone — dzięki temu można
odróżnić problem sieciowy (brak Wi-Fi) od problemu z brokerem/sesją MQTT.

```cpp
bool ok = mqttClient.connect(
    deviceId.c_str(),
    statusTopic.c_str(),   // will topic
    0,                      // will QoS
    true,                   // will retained
    willPayload.c_str()     // will payload ("offline")
);
if (ok) {
    publishStatus("online");
}
```

---

## 4. Last Will and Testament (LWT)

Przy każdym połączeniu z brokerem klient deklaruje komunikat awaryjny `offline`
na topicu statusowym (retained). Jeżeli ESP32 zniknie niepoprawnie (utrata
zasilania, restart, zerwanie sieci), broker sam opublikuje ten komunikat.
Dzięki retained flag nowy subskrybent (np. MQTT Explorer) od razu widzi ostatni
znany stan urządzenia.

---

## 5. Powrót do publikacji po reconnect

Pętla `loop()` nie blokuje się i po odzyskaniu połączenia automatycznie wraca do
cyklicznej publikacji pomiarów (co `MEASUREMENT_PERIOD_MS` = 5000 ms):

```cpp
void loop() {
    connectWiFiIfNeeded();
    syncNtpIfNeeded();
    connectMqttIfNeeded();
    mqttClient.loop();
    if (millis() - lastMeasurementMs > MEASUREMENT_PERIOD_MS) {
        lastMeasurementMs = millis();
        publishMeasurements();
    }
}
```

Pomiary są pomijane, dopóki nie ma synchronizacji NTP — gwarantuje to poprawne
pole `ts_ms` (Unix epoch) w wiadomościach pomiarowych.

---

## 6. Scenariusze testów awarii

### F1. Test utraty Wi-Fi
1. Po poprawnym starcie odłącz/wyłącz sieć Wi-Fi (lub zmień hasło na AP).
2. Oczekiwane: na `Serial` pojawia się `WiFi disconnected. Trying reconnect...`,
   próby co ~5 s, brak zawieszenia programu.
3. Po przywróceniu Wi-Fi: ponowna synchronizacja NTP, następnie reconnect MQTT i
   publikacja `online`.

### F2. Test niedostępnego brokera MQTT
1. Zatrzymaj broker (`docker compose stop broker`) lub ustaw błędny `MQTT_HOST`.
2. Oczekiwane: `blad TLS: ...` lub `blad, rc=...`, próby co ~3 s, Wi-Fi nadal działa.
3. Po przywróceniu brokera: połączenie wraca, publikowany jest `online`, wracają pomiary.

### F3. Test Last Will
1. W MQTT Explorer zasubskrybuj `lab/+/+/status`.
2. Połącz ESP32 — pojawia się retained `online`.
3. Odłącz zasilanie ESP32 (niepoprawne rozłączenie).
4. Oczekiwane: po wygaśnięciu keepalive broker publikuje `offline`.

### F4. Test powrotu do publikacji
Po przywróceniu warunków pracy sprawdź, że urządzenie znów publikuje `online`,
wraca cykliczna publikacja `temperature` i `pressure`, a topici są widoczne w
MQTT Explorer.

---

## 7. Parametry czasowe

| Parametr                 | Wartość | Znaczenie                          |
| ------------------------ | ------- | ---------------------------------- |
| `WIFI_RETRY_MS`          | 5000    | Odstęp między próbami reconnect Wi-Fi |
| `MQTT_RETRY_MS`          | 3000    | Odstęp między próbami reconnect MQTT  |
| `MEASUREMENT_PERIOD_MS`  | 5000    | Okres publikacji pomiarów          |
| `NTP_RETRY_MS`           | 10000   | Odstęp między próbami synchronizacji NTP |

---

## 8. Wnioski

- Brak Wi-Fi lub brak brokera nie powoduje zawieszenia firmware — pętla główna
  pozostaje responsywna, a próby reconnect są ograniczone czasowo.
- Rozdzielenie statusu (`online`/`offline`) od danych pomiarowych ułatwia
  diagnostykę stanu węzła.
- LWT z flagą retained pozwala wykryć nagłe zniknięcie urządzenia i odczytać jego
  ostatni stan natychmiast po podłączeniu subskrybenta.
- Synchronizacja NTP warunkuje publikację pomiarów, co gwarantuje poprawny
  znacznik czasu zgodny z kontraktem danych.

### Możliwe rozszerzenia (opcjonalne)
- osobny status `reconnecting`,
- licznik nieudanych prób połączenia w payloadzie statusowym,
- backoff o rosnącym opóźnieniu,
- wykorzystanie statusu urządzenia w warstwie backendowej/UI.
