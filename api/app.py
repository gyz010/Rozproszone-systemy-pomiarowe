from flask import Flask, jsonify
from psycopg2.extras import RealDictCursor
from db import get_connection
from models import MEASUREMENT_COLUMNS, measurements_to_list

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/measurements", methods=["GET"])
def get_measurements():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT {MEASUREMENT_COLUMNS}
            FROM measurements
            ORDER BY id DESC
            LIMIT 20;
        """)
        rows = cur.fetchall()
    conn.close()
    return jsonify(measurements_to_list(rows))


@app.route("/latest", methods=["GET"])
def get_latest():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT {MEASUREMENT_COLUMNS}
            FROM measurements
            ORDER BY id DESC
            LIMIT 1;
        """)
        rows = cur.fetchall()
    conn.close()
    return jsonify(measurements_to_list(rows))

@app.route("/devices", methods=["GET"])
def get_devices():
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT device_id
            FROM measurements
            ORDER BY device_id;
        """)
        results = cur.fetchall()
    conn.close()
    return jsonify(results)

@app.route("/measurements/<device_id>", methods=["GET"])
def get_measurements_by_device(device_id: str):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT {MEASUREMENT_COLUMNS}
            FROM measurements
            WHERE device_id = %s
            ORDER BY id DESC
            LIMIT 20;
        """, (device_id,))
        rows = cur.fetchall()
    conn.close()
    return jsonify(measurements_to_list(rows))

@app.route("/devices/<device_id>/sensors", methods=["GET"])
def get_sensors_by_device(device_id: str):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT sensor
            FROM measurements
            WHERE device_id = %s
            ORDER BY sensor;
        """, (device_id,))
        results = cur.fetchall()
    conn.close()
    return jsonify(results)

@app.route("/measurements/<device_id>/<sensor>", methods=["GET"])
def get_measurements_by_device_and_sensor(device_id: str, sensor: str):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT {MEASUREMENT_COLUMNS}
            FROM measurements
            WHERE device_id = %s AND sensor = %s
            ORDER BY id DESC
            LIMIT 20;
        """, (device_id, sensor))
        rows = cur.fetchall()
    conn.close()
    return jsonify(measurements_to_list(rows))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
