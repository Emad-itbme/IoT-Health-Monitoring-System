#!/usr/bin/env python3
"""
System Metrics Publisher
Publishes CPU and Memory usage to MQTT broker
Accessible from both local and remote networks
"""
import time
import psutil
import paho.mqtt.client as mqtt

# MQTT Configuration
# For LOCAL NETWORK: use 192.168.0.2 (your machine's local IP)
# For EXTERNAL/INTERNET: use 195.174.160.31 (external IP)
BROKER = "192.168.0.2"  # Change to 195.174.160.31 for external access
PORT = 1883

import socket
CLIENT_ID = f"system-monitor-{socket.gethostname()}"

# Topics for different metrics
SYSTEM_MEM_TOPIC = 'copilot/data/system/memory'
SYSTEM_CPU_TOPIC = 'copilot/data/system/cpu'

# Connect handler
def on_connect(client, userdata, flags, rc):
    print(f"System Monitor connected to MQTT broker at {BROKER}:{PORT} with code {rc}")
    if rc != 0:
        print(f"Connection failed with code {rc}")

# Disconnect handler
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection: {rc}")

# Create client with protocol version 4 (MQTTv3.1.1)
# Use callback_api_version to avoid deprecation warning
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

try:
    print(f"Attempting to connect to {BROKER}:{PORT}")
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    # Give connection time to establish
    time.sleep(0.5)
    
    print("System monitor started - publishing metrics every 5 seconds")
    

    # Use a non-blocking, fast loop for metrics
    import json
    while True:
        try:
            ram_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent(interval=None)  # Non-blocking, last value
            ram_payload = json.dumps({"value": round(ram_usage, 2)})
            cpu_payload = json.dumps({"value": round(cpu_usage, 2)})
            client.publish(SYSTEM_MEM_TOPIC, ram_payload, qos=1, retain=True)
            client.publish(SYSTEM_CPU_TOPIC, cpu_payload, qos=1, retain=True)
            print(f"Published - RAM: {ram_usage:.1f}% | CPU: {cpu_usage:.1f}%")
            time.sleep(0.5)  # Publish every 0.5 seconds
        except Exception as e:
            print(f"Error collecting/publishing system data: {e}")
            time.sleep(0.5)
            
except ConnectionRefusedError:
    print(f"ERROR: Could not connect to MQTT broker at {BROKER}:{PORT}")
    print("Make sure Mosquitto container is running on this host")
    print("Run: docker-compose up -d mosquitto")
except KeyboardInterrupt:
    print("\nShutting down system monitor...")
    client.loop_stop()
    client.disconnect()
    print("System monitor stopped")
except Exception as e:
    print(f"Error: {e}")
    client.loop_stop()
    client.disconnect()