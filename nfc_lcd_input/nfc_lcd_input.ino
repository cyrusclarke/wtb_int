//! WTB integrated version 16th August 2025 Cyrus Clarke
//with toggle switch for 2 screen types

#include <Wire.h>
#include <SPI.h>
#include <MFRC522.h>

// === CONFIG FLAG ===
// Uncomment the one you want to compile for
// #define USE_ADAFRUIT_BACKPACK   // Adafruit MCP23008-based
#define USE_GENERIC_BACKPACK    // Common PCF8574-based

// --- MFRC522 (SPI) pins
#define RC522_CS    44
#define RC522_RST   43
#define SPI_SCK      7
#define SPI_MOSI     9
#define SPI_MISO     8

// I2C pins (ESP32)
#define I2C_SDA      5
#define I2C_SCL      6

// Timeout before resetting to idle screen
const unsigned long IDLE_TIMEOUT_MS = 10000;

#ifdef USE_ADAFRUIT_BACKPACK
  #include <Adafruit_LiquidCrystal.h>
  Adafruit_LiquidCrystal lcd(0);   // MCP23008 backpack, ID=0
#elif defined(USE_GENERIC_BACKPACK)
  #include <LiquidCrystal_I2C.h>
  #define LCD_ADDR 0x27            // Common default for PCF8574
  LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
#endif

MFRC522 mfrc522(RC522_CS, RC522_RST);

unsigned long lastScanMillis = 0;
bool showingIdle = true;
String lastUID = "";

// --- Utilities ---
String uidHex(const MFRC522::Uid &u){
  String s;
  for (byte i=0;i<u.size;i++){
    if (u.uidByte[i] < 0x10) s += '0';
    s += String(u.uidByte[i], HEX);
  }
  s.toUpperCase();
  return s;
}

void showIdleScreen() {
  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("Hello Farcaster!");
  lcd.setCursor(0,1);
  lcd.print("Ready to Scan:");
  showingIdle = true;
}

// --- Setup ---
void setup(){
  Serial.begin(115200);

  // I2C init
  Wire.begin(I2C_SDA, I2C_SCL);

#ifdef USE_ADAFRUIT_BACKPACK
  lcd.begin(16, 2);
  lcd.display();
  lcd.setBacklight(HIGH);
#elif defined(USE_GENERIC_BACKPACK)
  lcd.init();
  lcd.backlight();
#endif

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("LCD Ready");
  delay(800);
  showIdleScreen();

  // SPI init (NFC)
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, RC522_CS);
  mfrc522.PCD_Init();
  delay(80);

  Serial.println("Hello Farcaster");
  lastScanMillis = millis();
}

// --- Loop ---
void loop(){
  checkSerialInput();

  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uid = uidHex(mfrc522.uid);
    if (uid != lastUID) {
      Serial.println("SCAN," + uid);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Tag:");
      lcd.setCursor(0, 1);
      lcd.print(uid.substring(0, 16));

      lastUID = uid;
    }

    showingIdle = false;
    lastScanMillis = millis();
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    delay(200);
  }

  if (!showingIdle && (millis() - lastScanMillis >= IDLE_TIMEOUT_MS)) {
    showIdleScreen();
  }

  delay(5);
}

void checkSerialInput() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("DISPLAY:")) {
      String message = input.substring(8);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(message.substring(0, 16));
      if (message.length() > 16) {
        lcd.setCursor(0, 1);
        lcd.print(message.substring(16, 32));
      }
    }
  }
}