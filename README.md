# iot-timeseries-demo

Demo stack TimescaleDB - Grafana

**Microcontrolador → MQTT → TimescaleDB → Grafana**

Todo el stack corre con un solo comando usando Docker.

---

## Stack

| Módulo | Tecnología | Rol |
|--------|-----------|-----|
| `input/` | Python + paho-mqtt | Escucha mensajes MQTT e inserta en la DB |
| `source/` | TimescaleDB (PostgreSQL) | Almacena series temporales |
| `output/` | Grafana | Visualización con dashboard precargado |
| `simulator/` | Python | Simula el sensor sin necesidad de hardware externo |
| Broker | Eclipse Mosquitto | Recibe los mensajes del microcontrolador |

---

## Levantar la demo

### Prerequisitos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose instalados

Con Docker no necesitás configurar nada más en tu entorno — todo el stack corre en contenedores.

### Iniciar el stack

```bash
git clone https://github.com/lvirginillo/iot-timeseries-demo
cd iot-timeseries-demo
docker compose up --build
```

Servicios disponibles:

| Servicio | URL / Puerto |
|----------|-------------|
| Grafana | http://localhost:3000 (admin / admin) |
| TimescaleDB | localhost:5432 |
| MQTT Broker | localhost:1883 |

---

## Conectar el microcontrolador

El listener espera mensajes MQTT en el topic `iot/#`.

### Formato del payload (JSON)

```json
{
  "device_id": "esp01", //o el micro que sea
  "metric": "temperature", //ejemplo de datos
  "value": 23.4
}
```

### Alternativa: topic estructurado

También podés publicar en `iot/<device_id>/<metric>` con solo el valor como payload:

```
topic:   iot/esp01/temperature
payload: 23.4
```

### Ejemplo desde Arduino / ESP32 (con librería PubSubClient)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* mqtt_server = "192.168.x.x"; // IP del servidor (PC de pruebas)

void publishSensor(float value) {
    StaticJsonDocument<128> doc;
    doc["device_id"] = "esp32-01";
    doc["metric"]    = "temperature";
    doc["value"]     = value;

    char buffer[128];
    serializeJson(doc, buffer);
    client.publish("iot/esp32-01/temperature", buffer);
}
```

### Probar sin hardware (mosquitto_pub)

```bash
mosquitto_pub -h localhost -t "iot/esp01/temperature" \
  -m '{"device_id":"esp32-01","metric":"temperature","value":23.4}'
```

---

## Simulator — probar sin microcontrolador ni sensor real

El directorio `simulator/` permite usar el proyecto completo sin necesidad de hardware externo.

### Requisitos

```bash
pip install -r requirements.txt
```

### sensor.py — publicar datos en tiempo real

En este ejemplo, lee la temperatura de CPU de una Raspberry Pi y la publica por MQTT cada N segundos, cumpliendo el mismo rol que un dispositivo externo.

```bash
python simulator/sensor.py
# opciones:
python simulator/sensor.py --broker localhost --interval 10 --device raspi
```

### import_csv.py — cargar historial desde CSV

En este caso, como ya tenia datos historicos, cargamos un archivo CSV con las lecturas directamente en TimescaleDB, sin pasar por MQTT. Útil para poblar el dashboard con datos reales desde el primer arranque, evitando tener que esperar la visualizacion final solo con datos nuevos.

Formato esperado del CSV:
```
2025-10-21 23:22:30, 40.4
2025-10-21 23:25:01, 40.8
```

```bash
python simulator/import_csv.py --csv /ruta/al/archivo.csv
# opciones:
python simulator/import_csv.py --csv datos.csv --device mi-sensor
```

---

## Visualización en Grafana

1. Abrí http://localhost:3000 (o la IP del servidor)
2. Login: `admin` / `admin`
3. El dashboard **IoT Sensor Data** ya está precargado

Incluye:
- Serie temporal de todos los valores recibidos
- Contador de mensajes en la última media hora
- Intervalo promedio entre mensajes

Para agregar tus propias métricas, editá el dashboard o creá uno nuevo usando el datasource **TimescaleDB** que ya está configurado.

---

## Estructura del repo

```
iot-timeseries-demo/
├── input/
│   ├── mqtt_listener.py     # suscribe al broker e inserta en TimescaleDB
│   └── Dockerfile
├── simulator/
│   ├── sensor.py            # publica temperatura de CPU por MQTT (reemplaza el hardware)
│   └── import_csv.py        # carga historial CSV directo a TimescaleDB
├── source/
│   └── init.sql             # crea la hypertable y los índices
├── output/
│   └── grafana/
│       └── provisioning/    # datasource + dashboard precargados
├── requirements.txt         # dependencias para simulator/
├── mosquitto.conf           # config del broker (anónimo para demo)
├── docker-compose.yml
└── README.md
```

---

## Extender el proyecto

**Cambiar el microcontrolador:** solo cambiás qué publica en MQTT. El resto del stack no cambia.

**Agregar métricas:** publicá en `iot/<device_id>/<nueva_metrica>`. Se almacena automáticamente.

**Autenticación MQTT:** editá `mosquitto.conf` para agregar usuario y contraseña.

**Retención de datos:** TimescaleDB tiene políticas de compresión y retención automática. Ver [docs](https://docs.timescale.com/use-timescale/latest/data-retention/).

---

## Licencia

MIT

## Autor: Lautaro Virginillo
inkedin.com/in/lautaro-virginillo
