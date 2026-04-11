#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

String line1 = "DDJ400 Bridge";
String line2 = "Waiting data...";
String line3 = "";
String line4 = "";

void drawScreen() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 12, line1.c_str());
  u8g2.drawStr(0, 28, line2.c_str());
  u8g2.drawStr(0, 44, line3.c_str());
  u8g2.drawStr(0, 60, line4.c_str());
  u8g2.sendBuffer();
}

String sanitizePart(String value) {
  value.replace("\r", "");
  value.replace("\n", " ");
  value.trim();
  if (value.length() > 21) {
    value = value.substring(0, 21);
  }
  return value;
}

void handleScreenCommand(String payload) {
  String parts[4] = {"", "", "", ""};
  int start = 0;

  for (int index = 0; index < 4; index++) {
    int separator = payload.indexOf('|', start);
    if (separator == -1) {
      parts[index] = payload.substring(start);
      start = payload.length();
    } else {
      parts[index] = payload.substring(start, separator);
      start = separator + 1;
    }
  }

  line1 = sanitizePart(parts[0]);
  line2 = sanitizePart(parts[1]);
  line3 = sanitizePart(parts[2]);
  line4 = sanitizePart(parts[3]);
  drawScreen();
}

void handleCommand(String command) {
  command.trim();

  if (command == "PING") {
    Serial.println("PONG OLED");
    return;
  }

  if (command.startsWith("SCREEN|")) {
    String payload = command.substring(7);
    handleScreenCommand(payload);
    Serial.println("OK");
    return;
  }

  Serial.println("ERR");
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  u8g2.begin();
  drawScreen();
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }
}
