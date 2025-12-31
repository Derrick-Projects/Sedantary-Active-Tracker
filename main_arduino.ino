// sedentary_tracker.ino
#include <Wire.h>
#include "RTClib.h"
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <math.h>

// ---------- Pin definitions ----------
const int PIR_PIN = 7;     // HC-SR501 OUT pin

// ---------- Objects ----------
RTC_DS3231 rtc;
Adafruit_MPU6050 mpu;

// ---------- Sedentary logic ----------
unsigned long lastMovementMillis = 0;
bool sedentaryAlerted = false;

// Motion sensitivity from MPU6050
const float MOVEMENT_THRESHOLD = 0.5; // m/s^2 change in magnitude

// Sedentary time threshold (FOR TESTING: 20 seconds)
const unsigned long SEDENTARY_THRESHOLD_MS = 20UL * 1000UL;

// For comparing acceleration
float lastAccelMagnitude = 0.0;

// ---- CSV logging settings ----
const unsigned long LOG_INTERVAL_MS = 1000UL; // log once per second

// Prints date-time in ISO-like format: YYYY-MM-DD HH:MM:SS
void printDateTime(const DateTime &dt) {
  Serial.print(dt.year());
  Serial.print("-");
  if (dt.month() < 10) Serial.print("0");
  Serial.print(dt.month());
  Serial.print("-");
  if (dt.day() < 10) Serial.print("0");
  Serial.print(dt.day());
  Serial.print(" ");

  if (dt.hour() < 10) Serial.print("0");
  Serial.print(dt.hour());
  Serial.print(":");
  if (dt.minute() < 10) Serial.print("0");
  Serial.print(dt.minute());
  Serial.print(":");
  if (dt.second() < 10) Serial.print("0");
  Serial.print(dt.second());
}

// Prints the same timestamp but into a char buffer (for CSV line)
void formatDateTime(char *out, size_t outSize, const DateTime &dt) {
  // "YYYY-MM-DD HH:MM:SS" = 19 chars + null terminator
  snprintf(out, outSize, "%04d-%02d-%02d %02d:%02d:%02d",
           dt.year(), dt.month(), dt.day(),
           dt.hour(), dt.minute(), dt.second());
}

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; }

  pinMode(PIR_PIN, INPUT);
  Wire.begin();

  Serial.println("Sedentary behavior tracker starting...");
  Serial.println("CSV format: timestamp,pir,deltaMag,inactiveSeconds,alerted");

  // --- Init RTC ---
  if (!rtc.begin()) {
    Serial.println("ERROR: Could not find DS3231 RTC!");
  } else {
    if (rtc.lostPower()) {
      Serial.println("RTC lost power, setting time to compile time.");
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
  }

  // --- Init MPU at 0x69 ---
  if (!mpu.begin(0x69)) {
    Serial.println("ERROR: Could not find MPU6050 at 0x69!");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  lastMovementMillis = millis();
}

void loop() {
  // 1) Read PIR
  int pirValue = digitalRead(PIR_PIN);
  bool pirMotion = (pirValue == HIGH);

  // 2) Read MPU6050 acceleration
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;

  float magnitude = sqrt(ax * ax + ay * ay + az * az);
  float deltaMag = fabs(magnitude - lastAccelMagnitude);
  lastAccelMagnitude = magnitude;

  bool mpuMotion = (deltaMag > MOVEMENT_THRESHOLD);

  // 3) Combine motion sources
  bool anyMotion = pirMotion || mpuMotion;

  unsigned long nowMillis = millis();
  if (anyMotion) {
    lastMovementMillis = nowMillis;
    sedentaryAlerted = false;
  }

  unsigned long inactiveTimeMs = nowMillis - lastMovementMillis;
  unsigned long inactiveSeconds = inactiveTimeMs / 1000UL;

  // 4) Get time
  DateTime now = rtc.now();

  // 5) Log status every 1s as CSV (easy to save to a file on your PC)
  static unsigned long lastLogMillis = 0;
  if (nowMillis - lastLogMillis >= LOG_INTERVAL_MS) {
    lastLogMillis = nowMillis;

    char ts[20];
    formatDateTime(ts, sizeof(ts), now);

    // CSV: timestamp,pir,deltaMag,inactiveSeconds,alerted
    Serial.print(ts);
    Serial.print(",");
    Serial.print(pirValue);
    Serial.print(",");
    Serial.print(deltaMag, 3);
    Serial.print(",");
    Serial.print(inactiveSeconds);
    Serial.print(",");
    Serial.println(sedentaryAlerted ? 1 : 0);
  }

  // 6) Sedentary alert (kept as human-readable block)
  if (inactiveTimeMs > SEDENTARY_THRESHOLD_MS && !sedentaryAlerted) {
    Serial.println("-------------------------------------------------");
    Serial.print("SEDENTARY ALERT at ");
    printDateTime(now);
    Serial.print(" - inactive for ");
    Serial.print(inactiveSeconds);
    Serial.println(" seconds.");
    Serial.println("-------------------------------------------------");
    sedentaryAlerted = true;
  }

  delay(100);
}
