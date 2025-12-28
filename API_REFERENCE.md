#  API Reference

Complete API documentation for all MQTT topics, HTTP endpoints, and Python modules.

## Table of Contents
- [MQTT Topics](#mqtt-topics)
- [InfluxDB Queries](#influxdb-queries)
- [Grafana API](#grafana-api)
- [Python Modules](#python-modules)
- [WebSocket Events](#websocket-events)

---

## MQTT Topics

### Sensor Data (Input)

#### `/medical/test/bpm`
**Heart Rate (Beats Per Minute)**

```json
{
  "value": 72.5,
  "timestamp": "2024-12-28T10:30:45Z",
  "unit": "bpm"
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `value` | float | 40-200 | Heart rate in beats per minute |
| `timestamp` | string | ISO 8601 | Optional: reading timestamp |
| `unit` | string | "bpm" | Optional: measurement unit |

**Quality Thresholds:**
-  Valid: 40-200 bpm
-  Warning: <40 or >150 bpm
-  Invalid: <20 or >200 bpm

---

#### `/medical/test/spo2`
**Oxygen Saturation (SpO2)**

```json
{
  "value": 98.2,
  "timestamp": "2024-12-28T10:30:45Z",
  "unit": "%"
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `value` | float | 80-100 | Blood oxygen saturation |
| `timestamp` | string | ISO 8601 | Optional: reading timestamp |
| `unit` | string | "%" | Optional: measurement unit |

**Quality Thresholds:**
-  Valid: 95-100%
-  Warning: 90-95%
-  Invalid: <80 or >100%

---

#### `/medical/test/temp`
**Body Temperature**

```json
{
  "value": 36.8,
  "timestamp": "2024-12-28T10:30:45Z",
  "unit": "°C"
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `value` | float | 35-40 | Body temperature in Celsius |
| `timestamp` | string | ISO 8601 | Optional: reading timestamp |
| `unit` | string | "°C" | Optional: measurement unit |

**Quality Thresholds:**
-  Valid: 36-37.5°C
-  Warning: 35-36 or 37.5-38.5°C
-  Invalid: <35 or >40°C

---

#### `/copilot/data/esp8266/rssi`
**WiFi Signal Strength (RSSI)**

```json
{
  "value": -65,
  "unit": "dBm"
}
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `value` | int | -30 to -120 | Signal strength in dBm |
| `unit` | string | "dBm" | Signal unit |

**Signal Quality:**
- Excellent: -30 to -67 dBm
- Good: -67 to -70 dBm
- Fair: -70 to -80 dBm
- Weak: <-80 dBm

---

### Validation Output

#### `/validation/sensor_quality`
**Real-time Validation Results**

```json
{
  "bpm": 1,
  "spo2": 1,
  "temp": 1,
  "anomaly_score": 0.05,
  "timestamp": "2024-12-28T10:30:45Z"
}
```

| Field | Type | Value | Description |
|-------|------|-------|-------------|
| `bpm` | int | 0\|1 | 1=Valid, 0=Invalid |
| `spo2` | int | 0\|1 | 1=Valid, 0=Invalid |
| `temp` | int | 0\|1 | 1=Valid, 0=Invalid |
| `anomaly_score` | float | 0-1 | Anomaly confidence (0=normal, 1=anomaly) |
| `timestamp` | string | ISO 8601 | Validation timestamp |

---

## InfluxDB Queries

### Flux Query Examples

#### Get Recent BPM Readings
```sql
from(bucket: "telegraf")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "medical/test/bpm")
  |> last()
```

#### Calculate Average SpO2 (Last Hour)
```sql
from(bucket: "telegraf")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "medical/test/spo2")
  |> mean()
```

#### Count Invalid Readings
```sql
from(bucket: "telegraf")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "validation/sensor_quality")
  |> filter(fn: (r) => r.is_valid == "0")
  |> count()
```

#### Detect Spikes in Heart Rate
```sql
from(bucket: "telegraf")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "medical/test/bpm")
  |> derivative(unit: 1m)
  |> filter(fn: (r) => r._value > 20)
```

---

## Grafana API

### Authentication
```bash
# Get API token
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user":"admin","password":"admin"}'

# Response
{
  "id": 1,
  "token": "eyJrIjoiYWJjZGVmZ2g..."
}
```

### Create Dashboard
```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

### Get Datasources
```bash
curl -X GET http://localhost:3000/api/datasources \
  -H "Authorization: Bearer $TOKEN"
```

### Create Alert
```bash
curl -X POST http://localhost:3000/api/alerts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard": {"title": "Heart Rate", "id": 1},
    "name": "High BPM Alert",
    "message": "BPM exceeded 150",
    "alertConditions": [{
      "evaluator": {"params": [150], "type": "gt"},
      "operator": {"type": "and"},
      "query": {"params": ["A", "5m", "now"]}
    }],
    "frequency": "60s",
    "handler": 1
  }'
```

---

## Python Modules

### `live_sensor_validator.py`

#### Class: `RealTimeValidator`

```python
from live_sensor_validator import RealTimeValidator

validator = RealTimeValidator()

# Validate a reading
result = validator.validate_reading(
    sensor_type='bpm',
    value=72.5,
    timestamp='2024-12-28T10:30:45Z'
)

# Returns
{
    'is_valid': True,
    'reason': 'Passed all validation layers',
    'confidence': 0.98,
    'anomaly_score': 0.05,
    'layers': {
        'range': True,
        'spike': True,
        'ml': True
    }
}
```

**Methods:**

```python
# Validate reading
validate_reading(sensor_type, value, timestamp)
  → Dict[str, Any]

# Get sensor config
get_sensor_config(sensor_type)
  → Dict[str, float]

# Update history
update_history(sensor_type, value)
  → None

# Reset validator
reset()
  → None
```

---

#### Class: `SensorValidator`

```python
from live_sensor_validator import SensorValidator
import paho.mqtt.client as mqtt

# Create client
client = SensorValidator(
    broker='localhost',
    port=1883,
    username=None,
    password=None
)

# Start listening
client.connect()
client.loop_forever()
```

**Events:**

```python
# On message received
def on_message(client, userdata, msg):
    """Called when message received"""
    print(f"Topic: {msg.topic}")
    print(f"Payload: {msg.payload.decode()}")

client.on_message = on_message
```

---

### `grafana_data_writer.py`

#### Class: `GrafanaDataWriter`

```python
from grafana_data_writer import GrafanaDataWriter

writer = GrafanaDataWriter(
    influx_host='localhost',
    influx_port=8086,
    influx_token='your-token'
)

# Write validation result
writer.write_validation(
    bpm_valid=True,
    spo2_valid=True,
    temp_valid=True
)

# Write sensor data
writer.write_sensor(
    measurement='medical/test/bpm',
    value=72.5,
    tags={'device': 'ESP8266'}
)
```

**Methods:**

```python
# Write to InfluxDB
write_point(point)
  → None

# Write validation result
write_validation(bpm_valid, spo2_valid, temp_valid, anomaly_score)
  → None

# Write sensor data
write_sensor(measurement, value, tags)
  → None

# Connect/disconnect
connect()
  → None

disconnect()
  → None
```

---

## WebSocket Events

### Real-time Sensor Updates

```javascript
// Connect to Grafana WebSocket
const ws = new WebSocket('ws://localhost:3000/api/live');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New reading:', data);
};

// Expected message format
{
  "channel": "medical/test/bpm",
  "data": {
    "value": 72.5,
    "timestamp": "2024-12-28T10:30:45Z"
  }
}
```

---

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| 400 | Invalid payload | JSON parsing failed |
| 401 | Unauthorized | Missing MQTT auth |
| 404 | Topic not found | Invalid topic name |
| 500 | Server error | InfluxDB write failed |
| 503 | Service unavailable | MQTT broker down |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| MQTT Publish | 1000 msgs | 1 minute |
| Grafana API | 100 requests | 1 minute |
| InfluxDB Query | 50 queries | 1 minute |

---

## Examples

### Complete MQTT Publishing

```bash
# Using mosquitto_pub
mosquitto_pub -h localhost \
  -t medical/test/bpm \
  -m '{"value": 72.5}'

# Using Python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect('localhost', 1883)

payload = {'value': 72.5}
client.publish('medical/test/bpm', json.dumps(payload))
```


---

See [README.md](README.md) for more information.
