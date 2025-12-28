#!/usr/bin/env python3
"""
ESP32 Temperature Simulator
Publishes simulated temperature data to MQTT broker
Accessible from both local and remote networks
"""
import time
import json
import random
from paho.mqtt import client as mqtt

# MQTT Configuration
# For LOCAL NETWORK: use 192.168.0.2 (your machine's local IP)
# For EXTERNAL/INTERNET: use 195.174.160.31 (external IP)
# For ESP32 on same network: use the local IP above
BROKER = "192.168.0.2"  # Change to 195.174.160.31 for external access
PORT = 1883  # Standard MQTT port
TOPIC = "medical/test/temp"
CLIENT_ID = "esp32-simulator"

# Connect handler
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker at {BROKER}:{PORT} with code {rc}")
    if rc != 0:
        print(f"Connection failed with code {rc}")

# Disconnect handler
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection: {rc}")
    else:
        print("Disconnected from MQTT broker")

# Create client with protocol version 4 (MQTTv3.1.1)
# Use callback_api_version to avoid deprecation warning
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
c.on_connect = on_connect
c.on_disconnect = on_disconnect

try:
    print(f"Attempting to connect to {BROKER}:{PORT}")
    c.connect(BROKER, PORT, 60)
    c.loop_start()
    
    # Give connection time to establish
    time.sleep(2)
    
    # Simulate temperature readings
    temp_value = 37.0
    publish_count = 0
    
    print(f"Starting to publish temperature data to {TOPIC}")
    
    while True:
        try:
            # Simulate realistic temperature fluctuation (±0.2°C per second)
            temp_value += random.uniform(-0.2, 0.2)
            # Keep temperature within realistic range
            temp_value = max(36.0, min(39.0, temp_value))
            
            # Publish as JSON with field name for Telegraf/InfluxDB
            payload = json.dumps({"value": round(temp_value, 2)})
            
            # Publish with QoS 1 (at least once) and retain flag for latecomer subscribers
            result = c.publish(TOPIC, payload, qos=1, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                publish_count += 1
                print(f"[{publish_count}] Published to {TOPIC}: {round(temp_value, 2)}°C")
            else:
                print(f"Failed to publish: {result.rc}")
            
            time.sleep(1)  # Publish every 1 second
            
        except Exception as e:
            print(f"Error publishing data: {e}")
            time.sleep(1)
            
except ConnectionRefusedError:
    print(f"ERROR: Could not connect to MQTT broker at {BROKER}:{PORT}")
    print("Make sure Mosquitto container is running on this host")
    print("Run: docker-compose up -d mosquitto")
except KeyboardInterrupt:
    print("\nShutting down publisher...")
    c.loop_stop()
    c.disconnect()
    print("Publisher stopped")
except Exception as e:
    print(f"Error: {e}")
    c.loop_stop()
    c.disconnect()