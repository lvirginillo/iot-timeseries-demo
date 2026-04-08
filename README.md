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

## Visualización en Grafana

1. Abrí http://localhost:3000
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
├── source/
│   └── init.sql             # crea la hypertable y los índices
├── output/
│   └── grafana/
│       └── provisioning/    # datasource + dashboard precargados
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
