#!/usr/bin/env python3
"""
Grafana Integration for Sensor Validation Results
Writes validation predictions to InfluxDB so they can be visualized in Grafana
"""

import json
import pickle
import numpy as np
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
from pathlib import Path
from collections import deque

# ============================================================================
# CONFIGURATION
# ============================================================================

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_VALIDATION_TOPIC = "validation/sensor_quality"

# InfluxDB Configuration
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "docker-token-d0d3a37e0a62cf2d58e3f50c76859cbe2e1c14ccd91f8ae0a7e0e5fa0c5d3c86"
INFLUXDB_ORG = "docker-me"
INFLUXDB_BUCKET = "telegraf"

# Model paths
MODEL_DIR = Path(__file__).parent / "models"

# ============================================================================
# INITIALIZE INFLUXDB CLIENT
# ============================================================================

def create_influx_client():
    """Create InfluxDB client"""
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        # Test connection
        client.ping()
        print(f" Connected to InfluxDB: {INFLUXDB_URL}")
        return client
    except Exception as e:
        print(f" InfluxDB connection error: {e}")
        print(f"   Make sure InfluxDB is running at {INFLUXDB_URL}")
        return None

# ============================================================================
# GRAFANA DATA WRITER
# ============================================================================

class GrafanaDataWriter:
    """Writes sensor validation data to InfluxDB for Grafana visualization"""
    
    def __init__(self, influx_client, broker, port):
        self.influx_client = influx_client
        self.write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        self.broker = broker
        self.port = port
        self.mqtt_client = mqtt.Client(client_id="grafana_data_writer")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.connected = False
    
    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            self.connected = True
            print(f" Connected to MQTT Broker: {self.broker}:{self.port}")
            client.subscribe(MQTT_VALIDATION_TOPIC, qos=1)
            print(f" Subscribed to: {MQTT_VALIDATION_TOPIC}")
        else:
            print(f" MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle validation messages and write to InfluxDB"""
        try:
            # Parse validation result
            payload_str = msg.payload.decode('utf-8')
            
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                print(f"  Invalid JSON payload: {payload_str} - {e}")
                return
            
            # Validate required fields
            if not all(key in payload for key in ['bpm', 'spo2', 'temp']):
                print(f"  Missing validation fields in payload: {payload}")
                return
            
            timestamp = payload.get("timestamp", datetime.now().isoformat())
            
            # Create InfluxDB points for each sensor
            points = []
            
            # BPM validation
            if "bpm" in payload:
                point = Point("sensor_validation") \
                    .tag("sensor", "bpm") \
                    .tag("measurement", "heart_rate") \
                    .field("is_valid", int(payload["bpm"])) \
                    .field("valid_status", "VALID" if payload["bpm"] == 1 else "INVALID") \
                    .time(timestamp)
                points.append(point)
            
            # SpO2 validation
            if "spo2" in payload:
                point = Point("sensor_validation") \
                    .tag("sensor", "spo2") \
                    .tag("measurement", "oxygen_saturation") \
                    .field("is_valid", int(payload["spo2"])) \
                    .field("valid_status", "VALID" if payload["spo2"] == 1 else "INVALID") \
                    .time(timestamp)
                points.append(point)
            
            # Temperature validation
            if "temp" in payload:
                point = Point("sensor_validation") \
                    .tag("sensor", "temp") \
                    .tag("measurement", "temperature") \
                    .field("is_valid", int(payload["temp"])) \
                    .field("valid_status", "VALID" if payload["temp"] == 1 else "INVALID") \
                    .time(timestamp)
                points.append(point)
            
            # Write to InfluxDB
            try:
                self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, records=points)
                
                # Print status
                status_str = f"BPM: {['❌','✅'][payload['bpm']]}, SpO2: {['❌','✅'][payload['spo2']]}, Temp: {['❌','✅'][payload['temp']]}"
                print(f" [{datetime.now().strftime('%H:%M:%S')}] {status_str} → Written to InfluxDB")
            except Exception as write_error:
                print(f"  Failed to write to InfluxDB: {write_error}")
        
        except Exception as e:
            print(f" Error processing message: {e}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client.connect(self.broker, self.port, keepalive=60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"❌ MQTT connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

# ============================================================================
# GRAFANA DASHBOARD CREATION
# ============================================================================

def create_grafana_dashboard_json():
    """Generate Grafana dashboard JSON for sensor validation visualization"""
    
    dashboard = {
        "dashboard": {
            "title": " Sensor Validation Dashboard",
            "tags": ["sensors", "validation", "healthcare"],
            "timezone": "UTC",
            "panels": [
                {
                    "title": "BPM Validation Status",
                    "type": "stat",
                    "gridPos": {"x": 0, "y": 0, "w": 8, "h": 4},
                    "targets": [
                        {
                            "refId": "A",
                            "measurement": "sensor_validation",
                            "select": [
                                [
                                    {"params": ["is_valid"], "type": "field"},
                                    {"params": [], "type": "mean"}
                                ]
                            ],
                            "tags": [{"key": "sensor", "value": "bpm"}]
                        }
                    ],
                    "options": {
                        "colorMode": "background",
                        "graphMode": "none",
                        "orientation": "auto",
                        "textMode": "auto",
                        "textAlign": "auto"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {
                                    "type": "value",
                                    "options": {
                                        "0": {"text": "INVALID", "color": "red"},
                                        "1": {"text": "VALID", "color": "green"}
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    "title": "SpO2 Validation Status",
                    "type": "stat",
                    "gridPos": {"x": 8, "y": 0, "w": 8, "h": 4},
                    "targets": [
                        {
                            "refId": "A",
                            "measurement": "sensor_validation",
                            "select": [
                                [
                                    {"params": ["is_valid"], "type": "field"},
                                    {"params": [], "type": "mean"}
                                ]
                            ],
                            "tags": [{"key": "sensor", "value": "spo2"}]
                        }
                    ],
                    "options": {
                        "colorMode": "background",
                        "graphMode": "none",
                        "orientation": "auto",
                        "textMode": "auto",
                        "textAlign": "auto"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {
                                    "type": "value",
                                    "options": {
                                        "0": {"text": "INVALID", "color": "red"},
                                        "1": {"text": "VALID", "color": "green"}
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    "title": "Temperature Validation Status",
                    "type": "stat",
                    "gridPos": {"x": 16, "y": 0, "w": 8, "h": 4},
                    "targets": [
                        {
                            "refId": "A",
                            "measurement": "sensor_validation",
                            "select": [
                                [
                                    {"params": ["is_valid"], "type": "field"},
                                    {"params": [], "type": "mean"}
                                ]
                            ],
                            "tags": [{"key": "sensor", "value": "temp"}]
                        }
                    ],
                    "options": {
                        "colorMode": "background",
                        "graphMode": "none",
                        "orientation": "auto",
                        "textMode": "auto",
                        "textAlign": "auto"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {
                                    "type": "value",
                                    "options": {
                                        "0": {"text": "INVALID", "color": "red"},
                                        "1": {"text": "VALID", "color": "green"}
                                    }
                                }
                            ]
                        }
                    }
                },
                {
                    "title": "Validation Quality Over Time",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 4, "w": 24, "h": 8},
                    "targets": [
                        {
                            "refId": "A",
                            "measurement": "sensor_validation",
                            "select": [
                                [
                                    {"params": ["is_valid"], "type": "field"},
                                    {"params": [], "type": "mean"}
                                ]
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    return dashboard

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print(" GRAFANA DATA WRITER SERVICE")
    print("=" * 70)
    
    # Initialize InfluxDB client
    influx_client = create_influx_client()
    if not influx_client:
        exit(1)
    
    # Create data writer
    writer = GrafanaDataWriter(influx_client, MQTT_BROKER, MQTT_PORT)
    
    # Connect to MQTT
    print(f"\n Connecting to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    if not writer.connect():
        exit(1)
    
    print("\n Service started. Listening for validation results...")
    print("   Data will be written to InfluxDB and visible in Grafana")
    print("   Press Ctrl+C to stop\n")
    
    # Print dashboard info
    print(" Grafana Dashboard:")
    print("   URL: http://localhost:3000")
    print("   Username: admin")
    print("   Password: admin")
    print("   Look for '🏥 Sensor Validation Dashboard'")
    
    try:
        while True:
            import time
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n Shutting down...")
        writer.disconnect()
        influx_client.close()
        print("✅ Service stopped")

if __name__ == "__main__":
    main()
