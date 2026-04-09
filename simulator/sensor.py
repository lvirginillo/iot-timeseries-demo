"""
sensor.py — lee la temperatura real de la CPU de la Raspi
y la publica por MQTT cada N segundos.

Uso:
    python sensor.py
    python sensor.py --interval 5 --broker localhost --device raspi
"""

import argparse
import json
import time
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--broker",   default="localhost",   help="MQTT broker host")
    p.add_argument("--port",     default=1883, type=int)
    p.add_argument("--topic",    default="iot/raspi/cpu_temp")
    p.add_argument("--device",   default="raspi")
    p.add_argument("--interval", default=10, type=float, help="Segundos entre lecturas")
    return p.parse_args()

def read_cpu_temp():
    with open(THERMAL_PATH) as f:
        return round(int(f.read().strip()) / 1000, 1)

def main():
    args = parse_args()

    client = mqtt.Client()
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()
    log.info(f"Connected to broker {args.broker}:{args.port}")
    log.info(f"Publishing to '{args.topic}' every {args.interval}s")

    while True:
        try:
            temp = read_cpu_temp()
            payload = json.dumps({
                "device_id": args.device,
                "metric":    "cpu_temp",
                "value":     temp,
                "time":      datetime.now(timezone.utc).isoformat()
            })
            client.publish(args.topic, payload)
            log.info(f"Published: {temp}°C")
        except Exception as e:
            log.error(f"Error: {e}")

        time.sleep(args.interval)

if __name__ == "__main__":
    main()
