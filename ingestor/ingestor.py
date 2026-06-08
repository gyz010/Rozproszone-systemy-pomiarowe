import json
import os
import paho.mqtt.client as mqtt
from db import get_connection

MQTT_HOST = "broker"
MQTT_PORT = 8883
MQTT_TOPIC = "lab/+/+/+"
CA_CERT_PATH = os.path.join(os.path.dirname(__file__), "certs", "ca.crt")

SENSOR_UNITS = {
    "temperature": "C",
    "pressure": "hPa",
}


def _is_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_non_negative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def parse_group_id_from_topic(topic):
    parts = topic.split("/")
    if len(parts) >= 4 and parts[0] == "lab":
        return parts[1]
    return None


def is_valid(data):
    required = ["device_id", "sensor", "value", "ts_ms"]
    if not all(field in data for field in required):
        return False

    if not _is_non_empty_string(data["device_id"]):
        return False

    if not _is_non_empty_string(data["sensor"]):
        return False

    if not _is_number(data["value"]):
        return False

    if not _is_positive_int(data["ts_ms"]):
        return False

    if "seq" in data and not _is_non_negative_int(data["seq"]):
        return False

    if "unit" in data:
        unit = data["unit"]
        if not isinstance(unit, str):
            return False
        expected_unit = SENSOR_UNITS.get(data["sensor"])
        if expected_unit is not None and unit != expected_unit:
            return False

    return True


def enrich_data_from_topic(topic, data):
    enriched = dict(data)
    if not enriched.get("group_id"):
        group_id = parse_group_id_from_topic(topic)
        if group_id:
            enriched["group_id"] = group_id
    return enriched


def save_measurement(topic, data):
    try:
        record = enrich_data_from_topic(topic, data)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO measurements 
            (group_id, device_id, sensor, value, unit, ts_ms, seq, topic)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            record.get("group_id"),
            record["device_id"],
            record["sensor"],
            record["value"],
            record.get("unit"),
            record["ts_ms"],
            record.get("seq"),
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
