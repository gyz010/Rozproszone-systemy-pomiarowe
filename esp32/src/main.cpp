#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <sys/time.h>
#include "secrets.h"

WiFiClient espClient;
PubSubClient mqttClient(espClient);
String deviceId;
String measurementTopic;
String statusTopic;

Adafruit_BMP280 bme;

// Timery i interwały (nieblokujące)
unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long lastMeasurementMs = 0;

const unsigned long WIFI_RETRY_MS = 5000;       // Próba Wi-Fi co 5s
const unsigned long MQTT_RETRY_MS = 3000;       // Próba MQTT co 3s
const unsigned long MEASUREMENT_PERIOD_MS = 5000; // Pomiary co 5s

String generateDeviceIdFromEfuse() {
    uint64_t chipId = ESP.getEfuseMac();
    char id[32];
    snprintf(id, sizeof(id), "esp32-%04X%08X",
             (uint16_t)(chipId >> 32),
             (uint32_t)chipId);
    return String(id);
}

// Pobieranie prawdziwego timestampu Unix w ms
long long getTimestampMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((long long)tv.tv_sec * 1000LL) + (tv.tv_usec / 1000);
}

// Funkcja pomocnicza do publikacji statusu (z flagą retained!)
void publishStatus(const char* state) {
    if (!mqttClient.connected()) return;

    StaticJsonDocument<128> doc;
    doc["device_id"] = deviceId;
    doc["status"] = state;
    doc["ts_ms"] = getTimestampMs();

    char buffer[128];
    serializeJson(doc, buffer, sizeof(buffer));
    
    // Publikacja jako retained (true), aby nowy klient od razu znał stan urządzenia
    mqttClient.publish(statusTopic.c_str(), buffer, true);
}

// Nieblokujące sprawdzanie i łączenie z Wi-Fi
void connectWiFiIfNeeded() {
    if (WiFi.status() == WL_CONNECTED) return;

    if (millis() - lastWifiAttemptMs < WIFI_RETRY_MS) return;
    lastWifiAttemptMs = millis();

    Serial.println("WiFi disconnected. Trying reconnect...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// Nieblokujące sprawdzanie i łączenie z MQTT wraz z Last Will
bool connectMqttIfNeeded() {
    if (WiFi.status() != WL_CONNECTED) return false; // MQTT wymaga działającego Wi-Fi
    if (mqttClient.connected()) return true;

    if (millis() - lastMqttAttemptMs < MQTT_RETRY_MS) return false;
    lastMqttAttemptMs = millis();

    Serial.print("Laczenie z MQTT...");

    // Przygotowanie payloadu dla Last Will and Testament (LWT)
    String willPayload = "{\"device_id\":\"" + deviceId + "\",\"status\":\"offline\"}";

    // Rejestracja LWT podczas łączenia z brokerem (retained = true dla offline)
    bool ok = mqttClient.connect(
        deviceId.c_str(),
        statusTopic.c_str(),
        0,                  // QoS 0
        true,               // Retained
        willPayload.c_str() // Wiadomość pośmiertna
    );

    if (ok) {
        Serial.println("OK");
        publishStatus("online"); // Natychmiastowe wysłanie statusu online
    } else {
        Serial.print("blad, rc=");
        Serial.println(mqttClient.state());
    }

    return ok;
}

void publishMeasurement() {
    if (!mqttClient.connected()) return;

    float temp = bme.readTemperature();

    StaticJsonDocument<256> doc;
    doc["device_id"] = deviceId;
    doc["sensor"] = "temperature";
    doc["value"] = temp;
    doc["unit"] = "C";
    doc["ts_ms"] = getTimestampMs(); // Użycie rzeczywistego czasu Unix

    char payload[256];
    serializeJson(doc, payload);
    mqttClient.publish(measurementTopic.c_str(), payload);
    
    Serial.print("Publikacja pomiaru: ");
    Serial.println(payload);
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    if (!bme.begin(0x76)) {
        Serial.println("Nie znaleziono czujnika BME280! Sprawdz polaczenia.");
    }

    deviceId = generateDeviceIdFromEfuse();
    
    // Konfiguracja osobnych topiców: pomiarowego i statusowego
    measurementTopic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/temperature";
    statusTopic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/status";

    Serial.print("Device ID: ");
    Serial.println(deviceId);

    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    
    // Pierwsza próba połączenia (inicjalna)
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
    // 1. Dbamy o łączność sieciową (nieblokująco)
    connectWiFiIfNeeded();
    connectMqttIfNeeded();
    
    // 2. Obsługa wewnętrznej pętli klienta MQTT (musi działać non-stop!)
    mqttClient.loop();

    // 3. Publikacja pomiarów przy użyciu millis() zamiast delay()
    if (millis() - lastMeasurementMs > MEASUREMENT_PERIOD_MS) {
        lastMeasurementMs = millis();
        publishMeasurement();
    }
}