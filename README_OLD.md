# ESP32 Real-time IoT Data Streaming with Grafana

**Status:** ✅ Fully Configured for External Network Access  
**External IP:** `195.174.160.31`  
**Dashboard URL:** `http://195.174.160.31:3000`

---

## 📋 Quick Links

- **Local Access:** `http://localhost:3000`
- **Remote Access:** `http://195.174.160.31:3000`
- **Setup Guide:** [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Credentials:** `admin` / `admin`

---

## 🎯 What This Does

This solution enables **real-time streaming** of sensor data from ESP32 devices (or simulated via pub.py) to a Grafana dashboard that's accessible from **anywhere on the internet**.

### Data Flow
```
ESP32 Device (pub.py simulator)
    ↓ MQTT Protocol (port 1883)
Mosquitto (MQTT Message Broker)
    ↓ JSON Parsing
Telegraf (Data Ingestion)
    ↓ Time-series Format
InfluxDB (Time-series Database)
    ↓ Flux Queries
Grafana (Real-time Dashboard)
    ↓ HTTP/WebSocket
Remote Users (195.174.160.31:3000)
```

---

## 🚀 Quick Start (5 minutes)

### 1️⃣ Start Docker Services
```bash
cd C:\Users\Emadr\Desktop\Iot_Server
docker-compose up -d
```

### 2️⃣ Start Data Simulators (separate terminals)

**Terminal A - Temperature Data:**
```bash
python Pub.py
```

**Terminal B - System Metrics:**
```bash
python system_mqtt_stream.py
```

### 3️⃣ View Dashboard
- **Local:** http://localhost:3000
- **Remote:** http://195.174.160.31:3000
- **Login:** admin / admin
- **Dashboard:** ESP32 Real-time IoT Dashboard

---

## 🔧 Configuration Details

### Services & Ports

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| **Mosquitto MQTT** | 1883 | External | ESP32 data ingestion |
| **Mosquitto WebSocket** | 9001 | External | Browser real-time updates |
| **InfluxDB API** | 8086 | Internal | Time-series storage & queries |
| **Grafana** | 3000 | External | Dashboard visualization |

### Key Features

✅ **Real-time Streaming** - 500ms refresh rate  
✅ **External Network Access** - Accessible from internet  
✅ **Automatic Data Source Setup** - Provisioned dashboards  
✅ **Persistent Storage** - InfluxDB with historical data  
✅ **Multiple Data Sources** - Medical, system metrics  
✅ **WebSocket Support** - Live updates in browser  
✅ **JSON Data Format** - Easy ESP32 integration  

---

## 📊 Data Streams

### Temperature Stream (pub.py)
- **Topic:** `medical/test/temp`
- **Format:** `{"value": 37.2, "timestamp": 1702460000}`
- **Frequency:** Every 1 second
- **Range:** 36.0°C - 39.0°C

### System Metrics (system_mqtt_stream.py)
- **CPU Topic:** `copilot/data/system/cpu`
- **RAM Topic:** `copilot/data/system/memory`
- **Format:** `{"usage": 45.2, "timestamp": 1702460000}`
- **Frequency:** Every 5 seconds

---

## 🔍 Monitoring

### Check Services Status
```bash
docker-compose ps
```

### View Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f grafana
docker-compose logs -f telegraf
docker-compose logs -f mosquitto
```

### Verify MQTT Data Flow
```bash
# Subscribe to all messages
docker exec -it mosquitto mosquitto_sub -h localhost -t "#" -v

# Subscribe to specific topic
docker exec -it mosquitto mosquitto_sub -h localhost -t "medical/test/temp"
```

### Check InfluxDB Data
```bash
# Access InfluxDB UI
# URL: http://localhost:8086
# Username: admin
# Password: (check docker-compose for token)
```

---

## 🛠️ Troubleshooting

### Problem: No data in Grafana

**Check 1: Are data publishers running?**
```bash
# Terminal A should show:
# [1] Published to medical/test/temp: {'value': 37.2, 'timestamp': 1702460000}
# [2] Published to medical/test/temp: {'value': 37.15, 'timestamp': 1702460001}

# Terminal B should show:
# Published - RAM: 32.5% | CPU: 15.2%
```

**Check 2: Is Mosquitto receiving data?**
```bash
docker exec -it mosquitto mosquitto_sub -h localhost -t "medical/#"
docker exec -it mosquitto mosquitto_sub -h localhost -t "copilot/#"
```

**Check 3: Is Telegraf writing to InfluxDB?**
```bash
docker logs telegraf | grep -i "write\|error" | tail -10
```

**Check 4: Dashboard time range**
- In Grafana, change time range to "Last 1 hour"
- Refresh the dashboard

### Problem: Cannot connect from remote network

**Check firewall:**
```powershell
# Windows Firewall - Allow port 1883 for MQTT
netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=tcp localport=1883
```

**Test external connection:**
```bash
# From remote machine
telnet 195.174.160.31 1883
# Should show connection (Ctrl+] then quit)
```

### Problem: Grafana won't start

```bash
# Check logs
docker logs grafana

# Restart
docker-compose restart grafana

# Rebuild if needed
docker-compose up -d --force-recreate grafana
```

---

## 📝 Customization

### Add New MQTT Topic

1. **Update Telegraf** (`telegraf/telegraf.conf`):
```ini
[[inputs.mqtt_consumer]]
  topics = [
    "medical/#",
    "copilot/data/#",
    "your/new/topic/#"  # Add here
  ]
```

2. **Restart Telegraf:**
```bash
docker-compose restart telegraf
```

3. **Add to Grafana dashboard** (create new panel)

### Adjust Refresh Rate

**For faster updates:**
```ini
[agent]
  interval = "100ms"      # Was 500ms
  flush_interval = "100ms"
```

**Warning:** Too fast may cause performance issues

### Change Grafana Password

```bash
# Inside Grafana container
docker exec -it grafana grafana-cli admin reset-admin-password <newpassword>
```

---

## 🔐 Security Recommendations

### For Production:

1. **Enable MQTT Authentication**
   ```conf
   # mosquitto/config/mosquitto.conf
   allow_anonymous false
   password_file /mosquitto/config/passwd
   ```

2. **Use TLS/SSL Certificates**
   ```conf
   listener 8883
   protocol mqtt
   certfile /mosquitto/certs/cert.pem
   keyfile /mosquitto/certs/key.pem
   ```

3. **Set Strong Grafana Password**
   ```bash
   docker exec -it grafana grafana-cli admin reset-admin-password <strong-password>
   ```

4. **Configure InfluxDB Authorization**
   - See InfluxDB UI: http://localhost:8086

5. **Firewall Rules**
   - Restrict ports to known IPs
   - Use VPN for sensitive data

---

## 📦 Project Structure

```
Iot_Server/
├── docker-compose.yml          # Service orchestration
├── Pub.py                       # Temperature simulator
├── system_mqtt_stream.py        # System metrics publisher
├── start.bat                    # Quick start script
├── verify_setup.py              # Verification script
├── SETUP_GUIDE.md               # Detailed setup
├── README.md                    # This file
│
├── mosquitto/
│   └── config/mosquitto.conf    # MQTT broker config
│
├── telegraf/
│   └── telegraf.conf            # Data ingestion config
│
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/         # Auto-provision data sources
│   │   └── dashboards/          # Auto-provision dashboards
│   └── data/                    # Grafana persistence
│
├── influxdb/
│   └── data/                    # Time-series database storage
│
└── nginx/                       # Optional reverse proxy
```

---

## 🧪 Verification

**Run the verification script:**
```bash
python verify_setup.py
```

This checks:
- ✓ Docker services running
- ✓ All ports accessible
- ✓ MQTT broker responding
- ✓ InfluxDB responding
- ✓ Configuration files present

---

## 📚 For Actual ESP32 Connection

Replace `localhost` with your server's IP in ESP32 code:

```cpp
const char* mqtt_server = "195.174.160.31";
const int mqtt_port = 1883;
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md#-for-actual-esp32-connection) for full ESP32 code example.

---

## 🔄 System Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart grafana

# Clean everything (⚠️ removes data!)
docker-compose down -v

# Rebuild images
docker-compose up -d --build

# Check service status
docker-compose ps
```

---

## 📞 Support

### For Issues:
1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md) troubleshooting section
2. Run `python verify_setup.py`
3. Check service logs: `docker-compose logs -f`

### Common Ports to Verify:
- MQTT: `1883`
- WebSocket: `9001`
- InfluxDB: `8086`
- Grafana: `3000`

---

## 📋 Checklist

- [ ] Docker is installed and running
- [ ] Services started with `docker-compose up -d`
- [ ] Pub.py is publishing data
- [ ] System monitor is running
- [ ] Grafana accessible at http://localhost:3000
- [ ] Dashboard shows temperature data
- [ ] Dashboard shows system metrics
- [ ] Remote access works at http://195.174.160.31:3000
- [ ] Data persists after service restart

---

## 🎉 You're All Set!

Your ESP32 real-time IoT streaming system is configured and ready. Start the services, publishers, and access your dashboard!

**Questions?** Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed documentation.

---

**Last Updated:** December 13, 2025  
**Status:** ✅ Production Ready  
**External IP:** 195.174.160.31
