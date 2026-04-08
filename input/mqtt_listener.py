import os
import json
import time
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config from environment ────────────────────────────────────────────────────
MQTT_BROKER   = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT     = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC    = os.getenv("MQTT_TOPIC", "iot/#")

DB_HOST       = os.getenv("DB_HOST", "timescaledb")
DB_PORT       = int(os.getenv("DB_PORT", 5432))
DB_NAME       = os.getenv("DB_NAME", "iot")
DB_USER       = os.getenv("DB_USER", "iot")
DB_PASSWORD   = os.getenv("DB_PASSWORD", "iot")

# ── DB connection (with retry) ─────────────────────────────────────────────────
def connect_db():
    for attempt in range(10):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT,
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            conn.autocommit = True
            log.info("Connected to TimescaleDB")
            return conn
        except psycopg2.OperationalError as e:
            log.warning(f"DB not ready (attempt {attempt + 1}/10): {e}")
            time.sleep(3)
    raise RuntimeError("Could not connect to TimescaleDB after 10 attempts")

conn = connect_db()

# ── Message handler ────────────────────────────────────────────────────────────
# Expected payload (JSON):
#   {"device_id": "esp32-01", "metric": "temperature", "value": 23.4}
# Topic structure: iot/<device_id>/<metric>  (payload can override both)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning(f"Invalid payload on {msg.topic}: {e}")
        return

    # Topic parts as fallback for device_id / metric
    parts = msg.topic.split("/")
    device_id = payload.get("device_id") or (parts[1] if len(parts) > 1 else "unknown")
    metric    = payload.get("metric")    or (parts[2] if len(parts) > 2 else "value")
    value     = payload.get("value")
    ts        = payload.get("time") or datetime.now(timezone.utc).isoformat()

    if value is None:
        log.warning(f"Missing 'value' in payload: {payload}")
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sensor_data (time, device_id, metric, value) VALUES (%s, %s, %s, %s)",
                (ts, device_id, metric, float(value))
            )
        log.info(f"Inserted → device={device_id} metric={metric} value={value}")
    except Exception as e:
        log.error(f"DB insert error: {e}")
        # Attempt reconnect
        global conn
        conn = connect_db()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"Connected to MQTT broker, subscribing to '{MQTT_TOPIC}'")
        client.subscribe(MQTT_TOPIC)
    else:
        log.error(f"MQTT connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    log.warning(f"Disconnected from MQTT broker (rc={rc}), reconnecting...")

# ── Main ───────────────────────────────────────────────────────────────────────
client = mqtt.Client()
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

while True:
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        log.error(f"MQTT error: {e}, retrying in 5s...")
        time.sleep(5)
