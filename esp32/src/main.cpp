#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include "secrets.h"

WiFiClient espClient;
PubSubClient mqttClient(espClient);
String deviceId;
String topic;

// Tworzenie obiektu BME280 (domyślnie dla interfejsu I2C)
Adafruit_BMP280 bme;

String generateDeviceIdFromEfuse()
{
    uint64_t chipId = ESP.getEfuseMac();
    char id[32];
    snprintf(id, sizeof(id), "esp32-%04X%08X",
             (uint16_t)(chipId >> 32),
             (uint32_t)chipId);
    return String(id);
}

void connectWiFi()
{
    Serial.print("Laczenie z Wi-Fi: ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("Polaczono z Wi-Fi");
    Serial.print("Adres IP: ");
    Serial.println(WiFi.localIP());
}

void connectMQTT()
{
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    while (!mqttClient.connected())
    {
        Serial.print("Laczenie z MQTT...");
        if (mqttClient.connect(deviceId.c_str()))
        {
            Serial.println("OK");
        }
        else
        {
            Serial.print("blad, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" - ponowna proba za 2 s");
            delay(2000);
        }
    }
}

void publishMeasurement()
{
    float temp = bme.readTemperature();
    // Możesz również odczytać inne parametry:
    // float hum = bme.readHumidity();
    // float pres = bme.readPressure() / 100.0F;

    StaticJsonDocument<256> doc;
    doc["device_id"] = deviceId;
    doc["sensor"] = "temperature";
    doc["value"] = temp;
    doc["unit"] = "C";
    doc["ts_ms"] = millis();
    char payload[256];
    serializeJson(doc, payload);
    mqttClient.publish(topic.c_str(), payload);
    Serial.print("Publikacja na topic: ");
    Serial.println(topic);
    Serial.println(payload);
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    // Inicjalizacja czujnika BME280 po I2C
    // Adres może różnić się w zależności od modułu (często 0x76 lub 0x77)
    if (!bme.begin(0x76)) {
        Serial.println("Nie znaleziono czujnika BME280! Sprawdz polaczenia.");
        // W razie problemów zatrzymaj program
        // while (1) delay(10);
    }

    deviceId = generateDeviceIdFromEfuse();
    topic = "lab/" + String(MQTT_GROUP) + "/" + deviceId + "/temperature";
    Serial.print("Device ID: ");
    Serial.println(deviceId);
    connectWiFi();
    connectMQTT();
}

void loop()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        connectWiFi();
    }
    if (!mqttClient.connected())
    {
        connectMQTT();
    }
    mqttClient.loop();
    publishMeasurement();
    delay(5000);
}