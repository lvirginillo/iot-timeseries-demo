"""
multi_device.py — simula múltiples dispositivos IoT publicando distintas métricas por MQTT.

Cada dispositivo publica: cpu_temp, cpu_usage, humidity, memory_pct.
Los valores usan patrones sinusoidales + ruido para que parezcan datos reales.

Uso:
    python simulator/multi_device.py
    python simulator/multi_device.py --broker localhost --interval 5
    python simulator/multi_device.py --devices esp32-01,esp32-02,esp32-03 --interval 3
"""

import argparse
import json
import math
import random
import time
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DEFAULT_DEVICES = ["esp32-01", "esp32-02", "esp32-03"]

# Offsets por dispositivo para que cada uno tenga un perfil distinto
DEVICE_PROFILES = {
    "esp32-01": {"cpu_temp": 0.0,   "cpu_usage": 0.0,  "humidity": 0.0,  "memory_pct": 0.0},
    "esp32-02": {"cpu_temp": 6.0,   "cpu_usage": 18.0, "humidity": 8.0,  "memory_pct": 12.0},
    "esp32-03": {"cpu_temp": -4.0,  "cpu_usage": 30.0, "humidity": -6.0, "memory_pct": 7.0},
}


def get_profile(device: str) -> dict:
    if device not in DEVICE_PROFILES:
        DEVICE_PROFILES[device] = {m: random.uniform(-6, 6) for m in ["cpu_temp", "cpu_usage", "humidity", "memory_pct"]}
    return DEVICE_PROFILES[device]


def simulate(metric: str, t: float, device: str) -> float:
    p = get_profile(device)

    if metric == "cpu_temp":
        # 35–80 °C, oscila cada ~2 min, picos esporádicos de carga
        base = 55 + p["cpu_temp"]
        wave = 10 * math.sin(t / 120)
        spike = random.uniform(5, 15) if random.random() < 0.04 else 0
        return round(max(30, min(90, base + wave + spike + random.gauss(0, 1.2))), 1)

    elif metric == "cpu_usage":
        # 5–95 %, picos de trabajo aleatorios
        base = 38 + p["cpu_usage"]
        wave = 22 * math.sin(t / 75)
        spike = random.uniform(20, 45) if random.random() < 0.06 else 0
        return round(max(1, min(99, base + wave + spike + random.gauss(0, 4))), 1)

    elif metric == "humidity":
        # 25–75 %, deriva lenta (ciclo ~5 min)
        base = 50 + p["humidity"]
        wave = 12 * math.sin(t / 300)
        return round(max(15, min(95, base + wave + random.gauss(0, 0.8))), 1)

    elif metric == "memory_pct":
        # 35–85 %, crece gradualmente, cae con GC ocasional
        base = 58 + p["memory_pct"]
        wave = 14 * math.sin(t / 200)
        gc_drop = -random.uniform(10, 25) if random.random() < 0.03 else 0
        return round(max(20, min(95, base + wave + gc_drop + random.gauss(0, 1.5))), 1)

    return 0.0


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--broker",   default="localhost",              help="MQTT broker host")
    p.add_argument("--port",     default=1883,        type=int)
    p.add_argument("--interval", default=5,           type=float,  help="Segundos entre publicaciones")
    p.add_argument("--devices",  default=",".join(DEFAULT_DEVICES), help="device_ids separados por coma")
    return p.parse_args()


def main():
    args = parse_args()
    devices = [d.strip() for d in args.devices.split(",")]
    metrics = ["cpu_temp", "cpu_usage", "humidity", "memory_pct"]

    client = mqtt.Client()
    client.connect(args.broker, args.port, keepalive=60)
    client.loop_start()

    log.info(f"Conectado a {args.broker}:{args.port}")
    log.info(f"Simulando {len(devices)} dispositivos | {len(metrics)} métricas cada uno | cada {args.interval}s")

    t0 = time.time()

    while True:
        t = time.time() - t0
        ts = datetime.now(timezone.utc).isoformat()

        for device in devices:
            readings = {}
            for metric in metrics:
                value = simulate(metric, t, device)
                readings[metric] = value
                topic = f"iot/{device}/{metric}"
                payload = json.dumps({
                    "device_id": device,
                    "metric":    metric,
                    "value":     value,
                    "time":      ts,
                })
                client.publish(topic, payload)

            log.info(
                f"[{device}] temp={readings['cpu_temp']}°C  "
                f"cpu={readings['cpu_usage']}%  "
                f"hum={readings['humidity']}%  "
                f"mem={readings['memory_pct']}%"
            )

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
