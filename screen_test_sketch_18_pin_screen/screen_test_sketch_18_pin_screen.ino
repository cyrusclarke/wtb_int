#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin(5, 6); // SDA=5, SCL=6
  delay(200);
  Serial.println("I2C scan...");
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found I2C device at 0x");
      Serial.println(addr, HEX);
      delay(5);
    }
  }
}
void loop() {}