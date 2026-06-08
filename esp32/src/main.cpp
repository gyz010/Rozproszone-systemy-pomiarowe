#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <sys/time.h>
#include <time.h>
#include "secrets.h"
#include "ca_cert.h"

#ifndef MQTT_TLS_CN
#define MQTT_TLS_CN "broker"
#endif

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);
String deviceId;
String statusTopic;

Adafruit_BMP280 bme;

unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long lastMeasurementMs = 0;
unsigned long lastNtpAttemptMs = 0;
uint32_t messageSeq = 0;

bool ntpSynced = false;
bool ntpConfigSent = false;

const unsigned long WIFI_RETRY_MS = 5000;
const unsigned long MQTT_RETRY_MS = 3000;
const unsigned long MEASUREMENT_PERIOD_MS = 5000;
const unsigned long NTP_RETRY_MS = 10000;

String generateDeviceIdFromEfuse() {
    uint64_t chipId = ESP.getEfuseMac();
    char id[32];
    snprintf(id, sizeof(id), "esp32-%04X%08X",
             (uint16_t)(chipId >> 32),
             (uint32_t)chipId);
    return String(id);
}

long long getTimestampMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((long long)tv.tv_sec * 1000LL) + (tv.tv_usec / 1000);
}

void syncNtpIfNeeded() {
    if (WiFi.status() != WL_CONNECTED || ntpSynced) {
        return;
    }

    if (millis() - lastNtpAttemptMs < NTP_RETRY_MS) {
        return;
    }
    lastNtpAttemptMs = millis();

    if (!ntpConfigSent) {
        configTime(0, 0, "pool.ntp.org", "time.nist.gov");
        ntpConfigSent = true;
        Serial.println("NTP: rozpoczecie synchronizacji czasu...");
    }

    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 500)) {
        ntpSynced = true;
        Serial.println("NTP: czas zsynchronizowany (Unix epoch aktywny).");
    } else {
        Serial.println("NTP: oczekiwanie na odpowiedz serwera...");
    }
}

String buildWillPayload() {
    JsonDocument doc;
    doc["group_id"] = MQTT_GROUP;
    doc["device_id"] = deviceId;
    doc["status"] = "offline";

    char buffer[192];
    serializeJson(doc, buffer, sizeof(buffer));
    return String(buffer);
}

void publishStatus(const char* state) {
    if (!mqttClient.connected()) {
        return;
    }

    JsonDocument doc;
    doc["group_id"] = MQTT_GROUP;
    doc["device_id"] = deviceId;
    doc["status"] = state;
    if (ntpSynced) {
        doc["ts_ms"] = getTimestampMs();
    }

    char buffer[192];
    serializeJson(doc, buffer, sizeof(buffer));

    mqttClient.publish(statusTopic.c_str(), buffer, true);
}

void connectWiFiIfNeeded() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    if (millis() - lastWifiAttemptMs < WIFI_RETRY_MS) {
        return;
    }
    lastWifiAttemptMs = millis();

    ntpSynced = false;
    ntpConfigSent = false;

    Serial.println("WiFi disconnected. Trying reconnect...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool connectMqttIfNeeded() {
    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }
    if (mqttClient.connected()) {
        return true;
    }

    if (millis() - lastMqttAttemptMs < MQTT_RETRY_MS) {
        return false;
    }
    lastMqttAttemptMs = millis();

    Serial.print("Laczenie z MQTT...");

    IPAddress brokerIp;
    if (!brokerIp.fromString(MQTT_HOST)) {
        Serial.println("blad: niepoprawny MQTT_HOST");
        return false;
    }

    if (!espClient.connected()) {
        if (!espClient.connect(brokerIp, MQTT_PORT, MQTT_TLS_CN, ca_cert, nullptr, nullptr)) {
            char tlsError[128];
            espClient.lastError(tlsError, sizeof(tlsError));
            Serial.print("blad TLS: ");
            Serial.println(tlsError);
            return false;
        }
    }

    String willPayload = buildWillPayload();

    bool ok = mqttClient.connect(
        deviceId.c_str(),
        statusTopic.c_str(),
        0,
        true,
        willPayload.c_str()
    );

    if (ok) {
        Serial.println("OK");
        publishStatus("online");
    } else {
        Serial.print("blad, rc=");
        Serial.println(mqttClient.state());
    }

    return ok;
}

void publishSensorMeasurement(const char* sensor, float value, const char* unit, long long timestampMs) {
    JsonDocument doc;
    doc["group_id"] = MQTT_GROUP;
    doc["device_id"] = deviceId;
    doc["sensor"] = sensor;
    doc["value"] = value;
    doc["unit"] = unit;
    doc["ts_ms"] = timestampMs;
    doc["seq"] = messageSeq++;

    char payload[320];
    serializeJson(doc, payload, sizeof(payload));

    String topic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/" + sensor;
    mqttClient.publish(topic.c_str(), payload);

    Serial.print("Publikacja pomiaru: ");
    Serial.println(payload);
}

void publishMeasurements() {
    if (!mqttClient.connected()) {
        return;
    }

    if (!ntpSynced) {
        Serial.println("Pomiar pominiety: brak synchronizacji NTP (ts_ms).");
        return;
    }

    long long timestampMs = getTimestampMs();
    publishSensorMeasurement("temperature", bme.readTemperature(), "C", timestampMs);
    publishSensorMeasurement("pressure", bme.readPressure() / 100.0F, "hPa", timestampMs);
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    if (!bme.begin(0x76)) {
        Serial.println("Nie znaleziono czujnika BMP280! Sprawdz polaczenia I2C.");
    }

    deviceId = generateDeviceIdFromEfuse();

    statusTopic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/status";

    Serial.print("Device ID: ");
    Serial.println(deviceId);
    Serial.print("Group ID: ");
    Serial.println(MQTT_GROUP);

    espClient.setCACert(ca_cert);
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

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
