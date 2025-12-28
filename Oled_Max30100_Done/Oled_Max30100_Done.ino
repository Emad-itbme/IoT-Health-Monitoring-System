#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "MAX30100_PulseOximeter.h"

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels
#define OLED_RESET -1    // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define NUMFLAKES 10 // Number of snowflakes in the animation example
#define LOGO_HEIGHT 16
#define LOGO_WIDTH 16

#define REPORTING_PERIOD_MS 500

PulseOximeter pox;
uint32_t tsLastReport = 0;

const unsigned char bitmap[] PROGMEM = {
  0x0f, 0xf8, 0x1f, 0xf0, 0x1f, 0xfc, 0x3f, 0xf8, 0x3f, 0xfe, 0x7f, 0xfc,
  0x78, 0x1f, 0xf0, 0x1e, 0xf0, 0x07, 0xe0, 0x0e, 0xe0, 0x07, 0xc4, 0x07,
  0xe0, 0x03, 0xce, 0x07, 0xc0, 0x03, 0xce, 0x07, 0xc0, 0x01, 0x9e, 0x03,
  0xc0, 0x00, 0x1f, 0x03, 0xc0, 0x00, 0x1f, 0x03, 0xc0, 0x0e, 0x3f, 0x03,
  0xe0, 0x0f, 0x3f, 0x07, 0xff, 0xdf, 0x3b, 0xff, 0xff, 0xdf, 0x3b, 0xff,
  0x7f, 0xff, 0xf3, 0xfe, 0x78, 0xfb, 0xf0, 0x3c, 0x3c, 0x73, 0xf0, 0x78,
  0x1e, 0x73, 0xe0, 0x78, 0x0f, 0x01, 0xe0, 0xf0, 0x07, 0x81, 0xe1, 0xe0,
  0x03, 0xc1, 0xc3, 0xc0, 0x01, 0xc1, 0xc7, 0x80, 0x00, 0xe0, 0x0f, 0x00,
  0x00, 0x70, 0x1e, 0x00, 0x00, 0x78, 0x3c, 0x00, 0x00, 0x3c, 0x3c, 0x00,
  0x00, 0x1e, 0x78, 0x00, 0x00, 0x0f, 0xf0, 0x00, 0x00, 0x07, 0xe0, 0x00,
  0x00, 0x07, 0xc0, 0x00, 0x00, 0x03, 0x80, 0x00
};

void onBeatDetected() {
  Serial.println("Beat!");
  display.drawBitmap(70, 27, bitmap, 32, 32, 1);
  display.display();
}

void setup() {
  Serial.begin(9600);

  // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  // Show initial display buffer contents on the screen
  display.display();
  delay(3000);

  // Clear the buffer
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(1);
  display.setCursor(0, 0);
  display.println("Initializing pulse oximeter..");
  display.display();

  Serial.print("Initializing pulse oximeter..");

  if (!pox.begin()) {
    Serial.println("FAILED");
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 0);
    display.println("FAILED");
    display.display();
    for(;;);
  } else {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 0);
    display.println("SUCCESS");
    display.display();
    Serial.println("SUCCESS");
  }

  pox.setOnBeatDetectedCallback(onBeatDetected);
}

void loop() {
  pox.update();

  if (millis() - tsLastReport > REPORTING_PERIOD_MS) {
    Serial.print("Heart BPM:");
    Serial.print(pox.getHeartRate());
    Serial.print("-----");
    Serial.print("Oxygen Percent:");
    Serial.print(pox.getSpO2());
    Serial.println("\n");

    display.clearDisplay();

    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 16);
    display.println(pox.getHeartRate());

    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 0);
    display.println("Heart BPM");

    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 30);
    display.println("Spo2");

    display.setTextSize(2);
    display.setTextColor(1);
    display.setCursor(0, 45);
    display.println(pox.getSpO2());

    display.display();

    tsLastReport = millis();
  }
}
