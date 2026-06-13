"""Pomocnicze mapowania rekordów bazy danych na słowniki dla REST API."""

# Wspólna lista kolumn pobieranych dla rekordu pomiaru.
# received_at jest formatowane do ISO 8601 (UTC) już na poziomie SQL.
MEASUREMENT_COLUMNS = """
    id, group_id, device_id, sensor, value, unit, ts_ms, seq, topic,
    to_char(received_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') as received_at
"""


def measurement_to_dict(row):
    return {
        "id": row[0],
        "group_id": row[1],
        "device_id": row[2],
        "sensor": row[3],
        "value": row[4],
        "unit": row[5],
        "ts_ms": row[6],
        "seq": row[7],
        "topic": row[8],
        "received_at": row[9],
    }


def measurements_to_list(rows):
    return [measurement_to_dict(row) for row in rows]
