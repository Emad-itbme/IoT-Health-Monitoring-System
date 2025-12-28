#!/usr/bin/env python3
"""
Real-Time Sensor Validation Service
Listens to NodeMCU sensor data via MQTT and publishes validation predictions
Integrates trained ML models for sensor quality assessment
"""

import json
import pickle
import numpy as np
import paho.mqtt.client as mqtt
from datetime import datetime
from collections import deque
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# MQTT Configuration (match MainScetch.ino)
MQTT_BROKER = "localhost"  # Change to your MQTT broker IP if remote
MQTT_PORT = 1883
MQTT_TIMEOUT = 60

# Input Topics (from NodeMCU)
MQTT_INPUT_TOPICS = {
    "medical/test/bpm": "bpm",
    "medical/test/spo2": "spo2",
    "medical/test/temp": "temp",
}

# Output Topic for validation results
MQTT_OUTPUT_TOPIC = "validation/sensor_quality"

# Model paths
MODEL_DIR = Path(__file__).parent / "models"

# History buffer size
MAX_HISTORY = 20

# ============================================================================
# LOAD MODELS AND THRESHOLDS
# ============================================================================

def load_models():
    """Load trained models and feature scaler from disk"""
    print(" Loading trained models...")
    
    try:
        # Load Random Forest model
        with open(MODEL_DIR / "random_forest_validator.pkl", "rb") as f:
            rf_model = pickle.load(f)
        print(" Random Forest model loaded")
        
        # Load Isolation Forest model
        with open(MODEL_DIR / "isolation_forest_anomaly.pkl", "rb") as f:
            iso_forest = pickle.load(f)
        print(" Isolation Forest model loaded")
        
        # Load Feature Scaler
        with open(MODEL_DIR / "feature_scaler.pkl", "rb") as f:
            scaler = pickle.load(f)
        print(" Feature Scaler loaded")
        
        # Load thresholds
        with open(MODEL_DIR / "thresholds.pkl", "rb") as f:
            thresholds = pickle.load(f)
        print(" Thresholds loaded")
        
        return rf_model, iso_forest, scaler, thresholds
    
    except FileNotFoundError as e:
        print(f" Model file not found: {e}")
        print(f"   Make sure to run the notebook first to train and save models")
        exit(1)

# ============================================================================
# REAL-TIME VALIDATOR CLASS
# ============================================================================

class RealTimeValidator:
    """
    Validates incoming sensor data in real-time
    Uses trained ML models for anomaly detection
    """
    
    def __init__(self, rf_model, iso_forest, scaler, thresholds):
        self.rf_model = rf_model
        self.iso_forest = iso_forest
        self.scaler = scaler
        self.thresholds = thresholds
        
        # History buffers
        self.bpm_history = deque(maxlen=MAX_HISTORY)
        self.spo2_history = deque(maxlen=MAX_HISTORY)
        self.temp_history = deque(maxlen=MAX_HISTORY)
        
        # Latest valid flags
        self.latest_validations = {
            "bpm": 1,
            "spo2": 1,
            "temp": 1,
            "timestamp": None
        }
        
        # Statistics
        self.predictions_made = 0
        self.predictions_invalid = 0
    
    def validate_reading(self, value, sensor_type):
        """
        Validate a single sensor reading
        Returns: 1 (valid) or 0 (invalid)
        """
        try:
            # Get thresholds for this sensor type
            min_val = self.thresholds[f"{sensor_type.upper()}_MIN"]
            max_val = self.thresholds[f"{sensor_type.upper()}_MAX"]
            spike_threshold = self.thresholds[f"{sensor_type.upper()}_SPIKE_THRESHOLD"]
            
            # Rule 1: Check basic physiological range
            if value < min_val or value > max_val:
                return 0, "out of range"
            
            # Rule 2: Check for spikes
            history = getattr(self, f"{sensor_type}_history")
            if len(history) > 0 and abs(float(value) - float(history[-1])) > spike_threshold:
                return 0, "spike detected"
            
            # Rule 3: Use ML model for fine-grained validation
            if len(history) >= 2:
                prev_values = list(history)[-5:]
                all_values = prev_values + [value]
                
                rolling_mean = np.mean(all_values)
                rolling_std = np.std(all_values)
                rolling_max = np.max(all_values)
                rolling_min = np.min(all_values)
                deviation = abs(float(value) - rolling_mean)
                abs_change = abs(float(value) - float(history[-1]))
                
                # Create feature vector
                features = np.array([[rolling_mean, rolling_std, rolling_max, rolling_min, deviation, abs_change]])
                features_scaled = self.scaler.transform(features)
                
                # ML prediction
                prediction = self.rf_model.predict(features_scaled)[0]
                
                if prediction == 0:
                    return 0, "ML model detected anomaly"
                else:
                    return 1, "valid (ML confirmed)"
            else:
                return 1, "valid (insufficient history)"
        
        except Exception as e:
            print(f"  Validation error for {sensor_type}: {e}")
            return 1, "error (defaulting to valid)"
    
    def process_reading(self, topic, value):
        """Process incoming sensor reading"""
        sensor_type = MQTT_INPUT_TOPICS[topic]
        
        # Add to history
        history = getattr(self, f"{sensor_type}_history")
        history.append(float(value))
        
        # Validate
        is_valid, reason = self.validate_reading(value, sensor_type)
        
        # Update latest
        self.latest_validations[sensor_type] = int(is_valid)
        self.latest_validations["timestamp"] = datetime.now().isoformat()
        
        # Statistics
        self.predictions_made += 1
        if is_valid == 0:
            self.predictions_invalid += 1
        
        # Print result
        status = "Valid" if is_valid else "İnvalid"
        print(f"  {status} {sensor_type.upper()}: {value:.2f} → {reason}")
        
        return is_valid
    
    def get_validation_payload(self):
        """Get current validation result as JSON"""
        return json.dumps(self.latest_validations)
    
    def print_stats(self):
        """Print validation statistics"""
        if self.predictions_made > 0:
            invalid_pct = (self.predictions_invalid / self.predictions_made) * 100
            print(f"\n Validation Statistics:")
            print(f"   Total predictions: {self.predictions_made}")
            print(f"   Invalid readings: {self.predictions_invalid} ({invalid_pct:.1f}%)")

# ============================================================================
# MQTT CLIENT
# ============================================================================

class SensorValidator:
    """MQTT client for sensor validation"""
    
    def __init__(self, broker, port, validator):
        self.broker = broker
        self.port = port
        self.validator = validator
        self.client = mqtt.Client(client_id="sensor_validator_service")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
    
    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            self.connected = True
            print(f"\n Connected to MQTT Broker: {self.broker}:{self.port}")
            
            # Subscribe to sensor topics
            for topic in MQTT_INPUT_TOPICS.keys():
                client.subscribe(topic, qos=1)
                print(f"    Subscribed to: {topic}")
            
            print(f"\nPublishing validation results to: {MQTT_OUTPUT_TOPIC}")
        else:
            print(f" Connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Decode payload
            payload_str = msg.payload.decode('utf-8')
            
            # Try to parse JSON first (from NodeMCU), then fallback to raw number
            try:
                payload_json = json.loads(payload_str)
                value = float(payload_json.get('value', payload_str))
            except (json.JSONDecodeError, ValueError, TypeError):
                # If not JSON, try parsing as raw number
                value = float(payload_str)
            
            topic = msg.topic
            
            print(f"\n [{datetime.now().strftime('%H:%M:%S')}] {topic}")
            
            # Validate reading
            self.validator.process_reading(topic, value)
            
            # Publish validation result
            validation_json = self.validator.get_validation_payload()
            result = self.client.publish(MQTT_OUTPUT_TOPIC, validation_json, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"    Validation published to {MQTT_OUTPUT_TOPIC}")
            else:
                print(f"     Failed to publish validation: {result.rc}")
        
        except (ValueError, TypeError) as e:
            print(f"  Invalid sensor value: {msg.payload} - {e}")
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {msg.payload} - {e}")
        except Exception as e:
            print(f"  Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection"""
        if rc != 0:
            print(f"\n  Unexpected disconnection from broker (code {rc})")
        self.connected = False
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            print(f" Connecting to MQTT Broker: {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=MQTT_TIMEOUT)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f" Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print(" REAL-TIME SENSOR VALIDATION SERVICE")
    print("=" * 70)
    
    # Load models
    rf_model, iso_forest, scaler, thresholds = load_models()
    
    # Create validator
    validator = RealTimeValidator(rf_model, iso_forest, scaler, thresholds)
    
    # Create MQTT client
    mqtt_client = SensorValidator(MQTT_BROKER, MQTT_PORT, validator)
    
    # Connect to broker
    if not mqtt_client.connect():
        exit(1)
    
    print("\nService started. Waiting for sensor data...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Keep running
        while True:
            import time
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n Shutting down...")
        validator.print_stats()
        mqtt_client.disconnect()
        print(" Service stopped")

if __name__ == "__main__":
    main()
