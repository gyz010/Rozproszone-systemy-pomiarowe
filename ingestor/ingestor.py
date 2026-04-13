import json
import paho.mqtt.client as mqtt
from db import get_connection

MQTT_HOST = "broker"
MQTT_PORT = 1883
MQTT_TOPIC = "lab/+/+/+"

def is_valid(data):
    required = ["device_id", "sensor", "value", "ts_ms"]
    return all(field in data for field in required)

def save_measurement(topic, data):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO measurements 
            (group_id, device_id, sensor, value, unit, ts_ms, seq, topic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("group_id"),
            data["device_id"],
            data["sensor"],
            data["value"],
            data.get("unit"),
            data["ts_ms"],
            data.get("seq"),
            topic
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Błąd zapisu do bazy: {e}")

def on_connect(client, userdata, flags, rc):
    print(f"Połączono z brokerem MQTT (kod: {rc})")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        
        if is_valid(data):
            save_measurement(msg.topic, data)
            print(f"Poprawnie zapisano wiadomość z: {msg.topic}")
        else:
            print(f"Niepoprawny format danych: {data}")
            
    except Exception as e:
        print(f"Błąd przetwarzania wiadomości: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Uruchamianie ingestora...")
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()