from flask import Flask, jsonify
import json
from psycopg2.extras import RealDictCursor
from db import get_connection
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/measurements", methods=["GET"])
def get_measurements():
    conn = get_connection() 
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, group_id, device_id, sensor, value, unit, ts_ms, seq, topic, 
                   to_char(received_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as received_at 
            FROM measurements
            ORDER BY id DESC
            LIMIT 20;
        """)
        results = cur.fetchall()
    conn.close()
    return jsonify(results)

@app.route("/latest", methods=["GET"])
def get_latest():
    conn = get_connection() 
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, group_id, device_id, sensor, value, unit, ts_ms, seq, topic, 
                   to_char(received_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as received_at 
            FROM measurements
            ORDER BY id DESC
            LIMIT 1;
        """)
        results = cur.fetchall()
    conn.close()
    return jsonify(results)

    
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)


