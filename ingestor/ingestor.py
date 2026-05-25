import json
import os
import paho.mqtt.client as mqtt
from db import get_connection

MQTT_HOST = "broker"
MQTT_PORT = 8883
MQTT_TOPIC = "lab/+/+/+"
CA_CERT_PATH = os.path.join(os.path.dirname(__file__), "certs", "ca.crt")

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

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Połączono z brokerem MQTT przez TLS (kod: {rc})")
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

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.tls_set(ca_certs=CA_CERT_PATH)
    client.on_connect = on_connect
    client.on_message = on_message

    print("Uruchamianie ingestora (TLS)...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
