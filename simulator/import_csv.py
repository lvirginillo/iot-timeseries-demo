"""
import_csv.py — carga el historial de temperatura_cpu.csv en TimescaleDB

Uso:
    python import_csv.py --csv ~/temperatura_cpu.csv
"""

import argparse
import csv
from datetime import datetime
import psycopg2

DB_HOST     = "localhost"
DB_PORT     = 5432
DB_NAME     = "iot"
DB_USER     = "iot"
DB_PASSWORD = "iot"
DEVICE_ID   = "raspi"
METRIC      = "cpu_temp"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Path al archivo CSV")
    p.add_argument("--device", default=DEVICE_ID, help="device_id (default: raspi)")
    return p.parse_args()

def main():
    args = parse_args()

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor()

    rows = []
    skipped = 0
    with open(args.csv, newline="", encoding="utf-8", errors="replace") as f:
        for line in f:
            # Elimina null bytes (corrupción UTF-16 / escritura parcial)
            line = line.replace("\x00", "").strip()
            if not line:
                continue
            # formato: "YYYY-MM-DD HH:MM:SS, 45.1"
            parts = line.split(",")
            if len(parts) < 2:
                continue
            raw_ts = parts[0].strip()
            # Corrige año duplicado (ej. "20252025-10-22" → "2025-10-22")
            if len(raw_ts) > 10 and raw_ts[:4] == raw_ts[4:8] and raw_ts[:4].isdigit():
                raw_ts = raw_ts[4:]
            try:
                ts    = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
                value = float(parts[1].strip())
                rows.append((ts, args.device, METRIC, value))
            except (ValueError, IndexError) as e:
                print(f"Skipping line: {line!r} ({e})")
                skipped += 1

    if not rows:
        print("No rows to import.")
        return

    cur.executemany(
        "INSERT INTO sensor_data (time, device_id, metric, value) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        rows
    )
    print(f"Imported {len(rows)} rows from {args.csv}" + (f" ({skipped} skipped)" if skipped else ""))
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
