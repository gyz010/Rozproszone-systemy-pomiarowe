#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

WiFiClient espClient;
PubSubClient mqttClient(espClient);
String deviceId;
String topic;
bool time_synchronised = false;

String generateDeviceIdFromEfuse() {
    uint64_t chipId = ESP.getEfuseMac();
    char id[32];
    snprintf(id, sizeof(id), "esp32-%04X%08X",
    (uint16_t)(chipId >> 32),
    (uint32_t)chipId);
    return String(id);
}


void connectWiFi() {
    Serial.print("Laczenie z Wi-Fi: ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("Polaczono z Wi-Fi");
    Serial.print("Adres IP: ");
    Serial.println(WiFi.localIP());
}


void connectMQTT() {
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    while (!mqttClient.connected()) {
        Serial.print("Laczenie z MQTT...");
        if (mqttClient.connect(deviceId.c_str())) {
            Serial.println("OK");
        } else {
            Serial.print("blad, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" - ponowna proba za 2 s");
            delay(2000);
        }
    }
}

void syncTimeNTP() {
    configTime(3600, 0, "pool.ntp.org", "time.nist.gov");
    struct tm timeinfo;
    while (!getLocalTime(&timeinfo)) {
        Serial.println("Oczekiwanie na synchronizacje czasu...");
        delay(500);
    }
    Serial.println("Czas zsynchronizowany.");
}

long long getTimestampMs() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((long long)tv.tv_sec * 1000LL) + (tv.tv_usec / 1000);
}

void publishMeasurement() {
    float internalTemp = temperatureRead();
    StaticJsonDocument<256> doc;
    doc["device_id"] = deviceId;
    doc["sensor"] = "temperature";
    doc["value"] = internalTemp;
    doc["unit"] = "C";
    doc["ts_ms"] = getTimestampMs();
    char payload[256];
    serializeJson(doc, payload);
    mqttClient.publish(topic.c_str(), payload);
    Serial.print("Publikacja na topic: ");
    Serial.println(topic);
    Serial.println(payload);
}



void setup() {
    Serial.begin(115200);
    delay(1000);
    deviceId = generateDeviceIdFromEfuse();
    topic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/temperature";
    Serial.print("Device ID: ");
    Serial.println(deviceId);
    connectWiFi();
    connectMQTT();

}






void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }
    if(!time_synchronised) {
        syncTimeNTP();
    }
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();
    

    publishMeasurement();
    delay(5000);
}