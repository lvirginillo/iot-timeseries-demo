# iot-timeseries-demo

Demo de un stack de monitoreo IoT en tiempo real. Los microcontroladores publican sus métricas por MQTT, un listener las persiste en TimescaleDB y Grafana las muestra en vivo. Actualmente lo uso para monitorear variables de una Raspberry Pi, pero el stack no está atado a ningún hardware en particular — podés conectar varios ESP32, Arduinos o cualquier dispositivo que hable MQTT en simultáneo, sin tocar nada del backend.

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

### multi_device.py — simular múltiples dispositivos (recomendado)

Simula 3 dispositivos ESP32 publicando 4 métricas cada uno por MQTT: temperatura de CPU, uso de CPU, humedad y uso de memoria. Los valores siguen patrones sinusoidales con ruido para imitar lecturas reales.

```bash
python simulator/multi_device.py
# opciones:
python simulator/multi_device.py --broker localhost --interval 5
python simulator/multi_device.py --devices esp32-01,esp32-02,esp32-03 --interval 3
```

Métricas publicadas por dispositivo:

| Métrica | Topic MQTT | Rango |
|---------|-----------|-------|
| `cpu_temp` | `iot/<device>/cpu_temp` | 30–90 °C |
| `cpu_usage` | `iot/<device>/cpu_usage` | 1–99 % |
| `humidity` | `iot/<device>/humidity` | 15–95 % |
| `memory_pct` | `iot/<device>/memory_pct` | 20–95 % |

### sensor.py — leer temperatura real de una Raspberry Pi

Lee la temperatura de CPU de la Raspberry Pi y la publica por MQTT cada N segundos, cumpliendo el mismo rol que un dispositivo externo.

```bash
python simulator/sensor.py
# opciones:
python simulator/sensor.py --broker localhost --interval 10 --device raspi
```

### import_csv.py — cargar historial desde CSV

Carga un archivo CSV con lecturas directamente en TimescaleDB, sin pasar por MQTT. Útil para poblar el dashboard con datos históricos desde el primer arranque.

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

El dashboard incluye:

| Panel | Tipo | Descripción |
|-------|------|-------------|
| Temperatura CPU — Raspberry Pi | Serie temporal | Lecturas de `sensor.py` separadas del resto |
| Temperatura CPU — ESP32s | Serie temporal | Lecturas simuladas por `multi_device.py` |
| Mensajes recibidos | Stat | Total de registros en el rango seleccionado |
| Intervalo promedio entre mensajes | Stat | Cadencia de publicación en segundos |
| Dispositivos activos (últ. 5 min) | Stat | Cantidad de devices con datos recientes |
| Temp CPU último / mínima / máxima | Stat | Resumen rápido con umbrales de color |
| Temperatura / CPU / Humedad por dispositivo | Gauge | Valor actual por device con escala verde→rojo |
| Uso de CPU / Humedad | Serie temporal | Evolución en el tiempo por dispositivo |
| Uso de memoria | Serie temporal | Con gradiente de relleno por dispositivo |

Para agregar tus propias métricas, publicá en `iot/<device_id>/<nueva_metrica>` y editá el dashboard usando el datasource **TimescaleDB** que ya está configurado.

---

## Estructura del repo

```
iot-timeseries-demo/
├── input/
│   ├── mqtt_listener.py     # suscribe al broker e inserta en TimescaleDB
│   └── Dockerfile
├── simulator/
│   ├── multi_device.py      # simula múltiples ESP32 con 4 métricas cada uno
│   ├── sensor.py            # publica temperatura de CPU real (Raspberry Pi)
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

## Imagenes de las pruebas

<img width="1314" height="538" alt="a serror" src="https://github.com/user-attachments/assets/23b32d66-2999-4ea7-9bc4-49614df7dd1d" />

<img width="1291" height="630" alt="1 28 K" src="https://github.com/user-attachments/assets/8b11090e-5c3f-4b55-9b69-00b7a3c8ad53" />

## Licencia

MIT

## Autor: Lautaro Virginillo
inkedin.com/in/lautaro-virginillo
