FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir paho-mqtt psycopg2-binary

COPY mqtt_listener.py .

CMD ["python", "mqtt_listener.py"]
