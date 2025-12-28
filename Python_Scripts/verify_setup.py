#!/usr/bin/env python3
"""
Verification Script for IoT Real-time Streaming Setup
Tests all components and validates configuration
"""

import os
import sys
import socket
import time
from datetime import datetime

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{CYAN}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

def check_port(host, port, timeout=2):
    """Test if a port is accessible"""
    try:
        socket.settimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def test_mqtt_connection(broker, port):
    """Test MQTT broker connection"""
    try:
        import paho.mqtt.client as mqtt
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                return True
            return False
        
        client = mqtt.Client(client_id="test-client")
        client.on_connect = on_connect
        client.connect(broker, port, 5)
        client.loop_start()
        time.sleep(1)
        client.loop_stop()
        return True
    except Exception as e:
        return False

def test_influxdb_connection(host, port):
    """Test InfluxDB connection"""
    try:
        import requests
        response = requests.get(f"http://{host}:{port}/api/v2/health", timeout=2)
        return response.status_code == 200
    except Exception as e:
        return False

def main():
    print(f"\n{CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  ESP32 IoT Real-time Streaming - Verification Script      ║")
    print("║  External IP: 195.174.160.31                              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    
    test_results = {}
    
    # ============================================================
    # 1. Network Connectivity
    # ============================================================
    print_section("1. Network Connectivity Tests")
    
    print("Testing local network (127.0.0.1)...")
    local_connectivity = check_port("127.0.0.1", 1883)
    if local_connectivity:
        print(f"{GREEN}✓ Local network accessible{RESET}")
        test_results['local_network'] = True
    else:
        print(f"{RED}✗ Local network NOT accessible{RESET}")
        test_results['local_network'] = False
    
    print("\nTesting external network (195.174.160.31)...")
    external_connectivity = check_port("195.174.160.31", 1883)
    if external_connectivity:
        print(f"{GREEN}✓ External network accessible{RESET}")
        test_results['external_network'] = True
    else:
        print(f"{YELLOW}⚠ External network NOT accessible (normal if localhost-only){RESET}")
        test_results['external_network'] = False
    
    # ============================================================
    # 2. Docker Services Status
    # ============================================================
    print_section("2. Docker Services Status")
    
    services = ['mosquitto', 'influxdb', 'telegraf', 'grafana']
    
    for service in services:
        try:
            import subprocess
            result = subprocess.run(
                ['docker', 'inspect', service],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"{GREEN}✓ {service.upper()} is running{RESET}")
                test_results[f'docker_{service}'] = True
            else:
                print(f"{RED}✗ {service.upper()} is NOT running{RESET}")
                test_results[f'docker_{service}'] = False
        except Exception as e:
            print(f"{YELLOW}⚠ Could not check {service}: {e}{RESET}")
            test_results[f'docker_{service}'] = False
    
    # ============================================================
    # 3. Port Connectivity
    # ============================================================
    print_section("3. Port Connectivity Tests")
    
    ports_to_test = [
        (1883, "MQTT"),
        (9001, "MQTT WebSocket"),
        (8086, "InfluxDB"),
        (3000, "Grafana")
    ]
    
    for port, service in ports_to_test:
        if check_port("127.0.0.1", port):
            print(f"{GREEN}✓ Port {port:5d} ({service:15s}) - OPEN{RESET}")
            test_results[f'port_{port}'] = True
        else:
            print(f"{RED}✗ Port {port:5d} ({service:15s}) - CLOSED{RESET}")
            test_results[f'port_{port}'] = False
    
    # ============================================================
    # 4. Service-specific Tests
    # ============================================================
    print_section("4. Service-specific Connection Tests")
    
    print("Testing MQTT Broker connection...")
    if test_mqtt_connection("127.0.0.1", 1883):
        print(f"{GREEN}✓ MQTT Broker responding correctly{RESET}")
        test_results['mqtt_functional'] = True
    else:
        print(f"{RED}✗ MQTT Broker NOT responding{RESET}")
        test_results['mqtt_functional'] = False
    
    print("\nTesting InfluxDB connection...")
    if test_influxdb_connection("127.0.0.1", 8086):
        print(f"{GREEN}✓ InfluxDB responding correctly{RESET}")
        test_results['influxdb_functional'] = True
    else:
        print(f"{YELLOW}⚠ InfluxDB NOT responding (may need setup){RESET}")
        test_results['influxdb_functional'] = False
    
    # ============================================================
    # 5. Configuration Files
    # ============================================================
    print_section("5. Configuration Files Status")
    
    config_files = [
        "docker-compose.yml",
        "Pub.py",
        "system_mqtt_stream.py",
        "telegraf/telegraf.conf",
        "mosquitto/config/mosquitto.conf",
        "grafana/provisioning/datasources/datasources.yml"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"{GREEN}✓ {config_file}{RESET}")
            test_results[f'config_{config_file}'] = True
        else:
            print(f"{RED}✗ {config_file} NOT FOUND{RESET}")
            test_results[f'config_{config_file}'] = False
    
    # ============================================================
    # 6. Summary
    # ============================================================
    print_section("6. Summary Report")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for v in test_results.values() if v)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"{GREEN}Passed: {passed_tests}{RESET}")
    print(f"{RED}Failed: {failed_tests}{RESET}")
    
    if passed_tests >= total_tests - 2:
        print(f"\n{GREEN}✓ System is READY for deployment!{RESET}")
        return 0
    elif passed_tests >= total_tests // 2:
        print(f"\n{YELLOW}⚠ System has some issues but may work{RESET}")
        return 1
    else:
        print(f"\n{RED}✗ System has critical issues{RESET}")
        return 2

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1)
