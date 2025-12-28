@echo off
REM Quick Start Script for ESP32 IoT Real-time Streaming
REM Windows PowerShell Version
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  ESP32 IoT Real-time Streaming - Quick Start               ║
echo ║  External IP: 195.174.160.31                               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

set IOT_SERVER_PATH=C:\Users\Emadr\Desktop\Iot_Server

echo [Step 1] Checking Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    pause
    exit /b 1
)
echo ✓ Docker found

echo.
echo [Step 2] Navigating to project directory...
cd /d %IOT_SERVER_PATH%
if %errorlevel% neq 0 (
    echo ERROR: Could not navigate to %IOT_SERVER_PATH%
    pause
    exit /b 1
)
echo ✓ In directory: %cd%

echo.
echo [Step 3] Pulling latest images...
docker-compose pull
if %errorlevel% neq 0 (
    echo WARNING: Could not pull images (may use cached versions)
)

echo.
echo [Step 4] Stopping existing containers...
docker-compose down
if %errorlevel% neq 0 (
    echo WARNING: Some containers may not have been cleaned up
)

echo.
echo [Step 5] Starting Docker services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    pause
    exit /b 1
)
echo ✓ Docker services started

echo.
echo [Step 6] Waiting for services to initialize...
timeout /t 5 /nobreak

echo.
echo [Step 7] Verifying services...
docker-compose ps


echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              ✓ Setup Complete!                             ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Next steps:
echo.
echo 1. START DATA PUBLISHERS (in separate terminals):
echo    Command 1: python Pub.py
echo    Command 2: python system_mqtt_stream.py
echo.
echo 2. OPEN GRAFANA DASHBOARD:
echo    Local:    http://localhost:3000
echo    Remote:   http://195.174.160.31:3000
echo    Login:    admin / admin
echo.
echo 3. VIEW DASHBOARD:
echo    Go to: Dashboards ^> ESP32 Real-time IoT Dashboard
echo.
echo Services are running on:
echo   - Mosquitto MQTT: port 1883 (ESP32 connections)
echo   - Mosquitto WebSocket: port 9001 (real-time streaming)
echo   - InfluxDB: port 8086 (time-series database)
echo   - Grafana: port 3000 (dashboard)
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
pause
