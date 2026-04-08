FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt psycopg2-binary

COPY mqtt_listener.py .

CMD ["python", "mqtt_listener.py"]
