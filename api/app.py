import time
from flask import Flask, jsonify, request
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
    from_ts = request.args.get('from_ts', type=int)
    to_ts = request.args.get('to_ts', type=int)
    limit = min(request.args.get('limit', default=20, type=int), 10000)

    conditions = ["device_id = %s", "sensor = %s"]
    params = [device_id, sensor]

    if from_ts is not None:
        conditions.append("ts_ms >= %s")
        params.append(from_ts)
    if to_ts is not None:
        conditions.append("ts_ms <= %s")
        params.append(to_ts)

    where_clause = " AND ".join(conditions)
    order = "ts_ms ASC" if (from_ts is not None or to_ts is not None) else "id DESC"
    params.append(limit)

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT {MEASUREMENT_COLUMNS}
            FROM measurements
            WHERE {where_clause}
            ORDER BY {order}
            LIMIT %s;
        """, params)
        rows = cur.fetchall()
    conn.close()
    return jsonify(measurements_to_list(rows))


@app.route("/devices/<device_id>/sensors/<sensor>/status", methods=["GET"])
def get_sensor_status(device_id: str, sensor: str):
    OFFLINE_THRESHOLD_MS = 30_000
    GAP_THRESHOLD_MS = 30_000
    WINDOW = 200

    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT MIN(ts_ms) AS first_seen_ms,
                   MAX(ts_ms) AS last_seen_ms,
                   COUNT(*)   AS total_count
            FROM measurements
            WHERE device_id = %s AND sensor = %s
        """, (device_id, sensor))
        summary = cur.fetchone()

        if summary["last_seen_ms"] is None:
            conn.close()
            return jsonify({"device_id": device_id, "sensor": sensor,
                            "is_online": False, "total_count": 0})

        cur.execute("""
            SELECT ts_ms FROM measurements
            WHERE device_id = %s AND sensor = %s
            ORDER BY ts_ms DESC LIMIT %s
        """, (device_id, sensor, WINDOW))
        rows = [r["ts_ms"] for r in cur.fetchall()]
    conn.close()

    rows.reverse()  # ascending

    now_ms = int(time.time() * 1000)
    last_seen_ms = summary["last_seen_ms"]
    last_seen_ago_ms = now_ms - last_seen_ms
    is_online = last_seen_ago_ms < OFFLINE_THRESHOLD_MS

    # Walk backwards through the window to find the most recent gap
    session_start_ms = rows[0]
    for i in range(len(rows) - 1, 0, -1):
        if rows[i] - rows[i - 1] > GAP_THRESHOLD_MS:
            session_start_ms = rows[i]
            break

    return jsonify({
        "device_id": device_id,
        "sensor": sensor,
        "is_online": is_online,
        "last_seen_ms": last_seen_ms,
        "last_seen_ago_s": round(last_seen_ago_ms / 1000, 1),
        "session_start_ms": session_start_ms,
        "session_uptime_s": round((last_seen_ms - session_start_ms) / 1000) if is_online else None,
        "first_seen_ms": summary["first_seen_ms"],
        "total_count": summary["total_count"],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
