#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "MAX30100_PulseOximeter.h"

// --- WiFi Configuration ---
const char* ssid     = "Hamza";
const char* password = "123456789";

// --- MQTT Configuration ---
const char* MQTT_HOST = "195.174.160.31";
const uint16_t MQTT_PORT = 1883;

// --- MQTT Topics ---

const char* TOPIC_BPM  = "medical/test/bpm";
const char* TOPIC_SPO2 = "medical/test/spo2";
const char* TOPIC_RSSI = "copilot/data/esp8266/rssi";
const char* TOPIC_Temp = "medical/test/temp";

// --- OLED Display Settings ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define SCREEN_ADDRESS 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- Pulse Oximeter Settings ---
PulseOximeter pox;
#define REPORTING_PERIOD_MS 200 // Send data every 1 second
uint32_t tsLastReport = 0;

// --- Network Objects ---
WiFiClient espClient;
PubSubClient mqtt(espClient);

// --- Bitmap for Heart Icon ---
const unsigned char bitmap [] PROGMEM = {
    0x0f, 0xf8, 0x1f, 0xf0, 0x1f, 0xfc, 0x3f, 0xf8, 0x3f, 0xfe, 0x7f, 0xfc, 0x78, 0x1f, 0xf0, 0x1e, 
    0xf0, 0x07, 0xe0, 0x0e, 0xe0, 0x07, 0xc4, 0x07, 0xe0, 0x03, 0xce, 0x07, 0xc0, 0x03, 0xce, 0x07, 
    0xc0, 0x01, 0x9e, 0x03, 0xc0, 0x00, 0x1f, 0x03, 0xc0, 0x00, 0x1f, 0x03, 0xc0, 0x0e, 0x3f, 0x03, 
    0xe0, 0x0f, 0x3f, 0x07, 0xff, 0xdf, 0x3b, 0xff, 0xff, 0xdf, 0x3b, 0xff, 0x7f, 0xff, 0xf3, 0xfe, 
    0x78, 0xfb, 0xf0, 0x3c, 0x3c, 0x73, 0xf0, 0x78, 0x1e, 0x73, 0xe0, 0x78, 0x0f, 0x01, 0xe0, 0xf0, 
    0x07, 0x81, 0xe1, 0xe0, 0x03, 0xc1, 0xc3, 0xc0, 0x01, 0xc1, 0xc7, 0x80, 0x00, 0xe0, 0x0f, 0x00, 
    0x00, 0x70, 0x1e, 0x00, 0x00, 0x78, 0x3c, 0x00, 0x00, 0x3c, 0x3c, 0x00, 0x00, 0x1e, 0x78, 0x00, 
    0x00, 0x0f, 0xf0, 0x00, 0x00, 0x07, 0xe0, 0x00, 0x00, 0x07, 0xc0, 0x00, 0x00, 0x03, 0x80, 0x00
};

// --- Callback for Heartbeat ---
void onBeatDetected() {
    Serial.println("Beat!");
    display.drawBitmap(85, 16, bitmap, 32, 32, 1);
    display.display();
}

// --- Connection Helpers ---
void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;
    Serial.print("Connecting to "); Serial.println(ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500); Serial.print(".");
    }
    Serial.println("\nWiFi connected");
}

void connectMQTT() {
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    while (!mqtt.connected()) {
        String clientId = "esp8266-health-" + String(ESP.getChipId(), HEX);
        Serial.print("Connecting to MQTT...");
        if (mqtt.connect(clientId.c_str())) {
            Serial.println("connected!");
        } else {
            Serial.print("failed, rc="); Serial.print(mqtt.state());
            Serial.println(" retrying in 1s");
            delay(1000);
        }
    }
}

// --- Publishing Helpers ---
void publishJsonLong(const char* topic, long value) {
  char payload[32];
  snprintf(payload, sizeof(payload), "{\"value\":%ld}", value);
  mqtt.publish(topic, payload, true);
}

void publishJsonFloat(const char* topic, float value, int decimals = 1) {
  char payload[32];
  snprintf(payload, sizeof(payload), "{\"value\":%.*f}", decimals, value);
  mqtt.publish(topic, payload, true); // retain
}

void setup() {
    Serial.begin(115200);

 if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  display.display();
  delay(3000);
  display.clearDisplay();
    // Initialize OLED
    if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        Serial.println(F("SSD1306 failed"));
        for(;;);
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(1);
    display.setCursor(0,0);
    display.println("Connecting WiFi...");
    display.display();

    connectWiFi();
    connectMQTT();

    // Initialize Pulse Oximeter
    display.clearDisplay();
    display.setCursor(0,0);
    display.println("Init MAX30100...");
    display.display();

    if (!pox.begin()) {
        Serial.println("MAX30100 FAILED");
        display.println("FAILED");
        display.display();
        for(;;);
    } else {
        Serial.println("MAX30100 SUCCESS");
        pox.setOnBeatDetectedCallback(onBeatDetected);
    }
}

void loop() {
    // Crucial: Update sensor as often as possible
    pox.update();
    
    // Maintain connections
    if (WiFi.status() != WL_CONNECTED) connectWiFi();
    if (!mqtt.connected()) connectMQTT();
    mqtt.loop();

    // Periodic Data Reporting (Logic from Code 1 & 2 merged)
    if (millis() - tsLastReport > REPORTING_PERIOD_MS) {
         
         float bpm  = pox.getHeartRate();
         float spo2 = pox.getSpO2();
         long rssi  = WiFi.RSSI();

            publishJsonFloat(TOPIC_BPM,  bpm,  1);
            publishJsonFloat(TOPIC_SPO2, spo2, 1);
            publishJsonLong (TOPIC_RSSI, rssi);

            float tempC = 36.5 + (float)random(0, 30) / 10.0;
            publishJsonFloat(TOPIC_Temp, tempC, 1);

        // 2. Update Serial
        Serial.print("Heart BPM: "); Serial.print(bpm);
        Serial.print(" | SpO2: "); Serial.println(spo2);

        // 3. Update OLED (Logic from Code 1)
        display.clearDisplay();  
        display.setTextSize(1);
        display.setCursor(0, 0);
        display.print("BPM:");
        display.setTextSize(2);
        display.setCursor(0, 10);
        display.print(bpm, 1);
        display.setTextSize(1);
        display.setCursor(0, 35);
        display.print("SpO2 %:");
        display.setTextSize(2);
        display.setCursor(0, 45);
        display.print(spo2, 1);
        display.display();
       
        tsLastReport = millis();
    }
}