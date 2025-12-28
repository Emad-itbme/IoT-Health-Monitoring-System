#!/usr/bin/env python3
"""
Test MQTT data to verify validator works
Simulates NodeMCU publishing sensor data
"""

import json
import time
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

def test_publish():
    """Publish test sensor data"""
    client = mqtt.Client(client_id="test_publisher")
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        print(f"✅ Connected to MQTT Broker")
        
        # Test data (simulating NodeMCU format)
        test_readings = [
            {"topic": "medical/test/bpm", "value": 72.5},
            {"topic": "medical/test/spo2", "value": 98.2},
            {"topic": "medical/test/temp", "value": 36.5},
            {"topic": "medical/test/bpm", "value": 73.1},
            {"topic": "medical/test/spo2", "value": 97.9},
            {"topic": "medical/test/temp", "value": 36.6},
        ]
        
        print("\n📨 Publishing test data (NodeMCU format with JSON):\n")
        
        for reading in test_readings:
            # Format exactly like NodeMCU does: {"value": XX.X}
            payload = json.dumps({"value": reading["value"]})
            
            client.publish(reading["topic"], payload, qos=1)
            print(f"  ✅ Published to {reading['topic']}: {payload}")
            time.sleep(1)
        
        print("\n✅ Test data published successfully!")
        print("   Validator should receive and validate these readings")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    test_publish()
