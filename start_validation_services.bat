@echo off
REM Start Real-Time Sensor Validation Services
REM This batch file starts both the validator and Grafana data writer

echo.
echo ========================================================================
echo  🏥 Starting Sensor Validation Services
echo ========================================================================
echo.

REM Navigate to Python Scripts directory
cd /d "C:\Users\Emadr\Desktop\Iot_Server\Python_Scripts"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the services in separate windows
echo Starting live_sensor_validator.py...
start "Sensor Validator" python live_sensor_validator.py

REM Wait a second then start the data writer
timeout /t 2 /nobreak

echo Starting grafana_data_writer.py...
start "Grafana Data Writer" python grafana_data_writer.py

echo.
echo ✅ Services started in separate windows
echo.
echo 📊 Access Grafana at: http://localhost:3000
echo    Username: admin
echo    Password: admin
echo.
echo 🛑 Close the terminal windows to stop the services
echo.
pause
