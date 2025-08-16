#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"
#include <HTTPClient.h>
#include <ArduinoJson.h>

#define DHTTYPE DHT22
#define DHTPIN 18
#define MQ4_PIN 32      
#define MQ135_PIN 35    
#define ledRedPin 33
#define ledGreenPin 27
#define ledOrangePin 5
#define buzzerPin 19

DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x27, 16, 2);

const char* ssid = "EMAGREENHOUSE";
const char* password = "greenhouse2025";
const char* mac_address = "3C:71:BF:49:2F:8A";

void WiFiconnect() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 3) {
        delay(10000);
        lcd.setCursor(0,0);
        lcd.print("WIFI CONNECTED");
        attempts++;
    }
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Failed to connect!");
        lcd.setCursor(0,0);
        lcd.print("WiFi Failed!");
        WiFi.disconnect(true);
    } else {
        Serial.printf("Connected! IP: %s\n", WiFi.localIP());
    }
}

bool WiFiisConnected() {
    return WiFi.status() == WL_CONNECTED;
}

void WiFicheckConnection() {
    if (!WiFiisConnected()) {
        digitalWrite(ledGreenPin, LOW);
        digitalWrite(ledRedPin, HIGH);
        WiFiconnect();
    } else {
        digitalWrite(ledRedPin, LOW);
        digitalWrite(ledGreenPin, HIGH);
    }
}


float tempThreshold = 0, humThreshold = 0, ch4Threshold = 0, co2Threshold = 0, noxThreshold = 0;

void getThresholds() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin("http://paulkys.local:8000/get_thresholds/");
        int httpCode = http.GET();
        if (httpCode == 200) {
            String payload = http.getString();
            StaticJsonDocument<256> doc;
            deserializeJson(doc, payload);
            if (doc["status"] == "success") {
                tempThreshold = doc["thresholds"]["temperature"];
                humThreshold = doc["thresholds"]["humidity"];
                ch4Threshold = doc["thresholds"]["ch4"];
                co2Threshold = doc["thresholds"]["co2"];
                noxThreshold = doc["thresholds"]["nox"];
                Serial.println("Thresholds updated!");
            }
        }
        http.end();
    }
}

void sendGSMAlert(float temp, float hum, float mq4, float mq135, String level) {
    Serial.println("Sending GSM alert...");
    
    Serial1.println("AT+CMGF=1"); 
    delay(100);
    Serial1.println("AT+CMGS=\"+263773735227\""); 
    delay(100);
    String msg = level + " ALERT! Temp:" + String(temp) + 
                 " Hum:" + String(hum) + " CH4:" + String(mq4) +
                 " CO2:" + String(mq135) + " NOx:" + String(mq4);
    Serial1.print(msg);
    delay(100);
    Serial1.write(26); 
}


void checkLocalThresholds(float temp, float hum, float mq4, float mq135) {
    // Reset LEDs
    digitalWrite(ledRedPin, LOW);
    digitalWrite(ledOrangePin, LOW);
    digitalWrite(buzzerPin, LOW);

    // CRITICAL
    if (temp > tempThreshold || hum > humThreshold || mq4 > ch4Threshold || mq135 > co2Threshold || mq135 > noxThreshold) {
        digitalWrite(ledRedPin, HIGH);
        digitalWrite(buzzerPin, HIGH);
        // sendGSMAlert(temp, hum, mq4,mq135,"CRITICAL"));
    } 
    // WARNING (90% of threshold)
    else if (temp > tempThreshold*0.9 || hum > humThreshold*0.9 || mq4 > ch4Threshold*0.9 || mq135 > co2Threshold*0.9 || mq135 > noxThreshold*0.9) {
        digitalWrite(ledOrangePin, HIGH);
        // sendGSMAlert(sendGSMAlert(temp, hum, mq4,mq135,"WARNING"));
    }
}


void setup() {
    Serial.begin(115200);
    delay(2000);
    pinMode(ledRedPin, OUTPUT);
    pinMode(ledGreenPin, OUTPUT);
    pinMode(ledOrangePin, OUTPUT);
    pinMode(buzzerPin, OUTPUT);

    WiFiconnect();
    dht.begin();

    lcd.init();
    lcd.backlight();
    lcd.setCursor(0,0);
    lcd.print("Connecting WiFi");
}

void loop() {
    WiFicheckConnection();
    static unsigned long lastThresholdFetch = 0;
  if (millis() - lastThresholdFetch > 300000) { 
    getThresholds();
    lastThresholdFetch = millis();
  }

   
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();

   
    if (isnan(temperature)) temperature = 0;
    if (isnan(humidity)) humidity = 0;

    int mq4 = analogRead(MQ4_PIN);
    int mq135 = analogRead(MQ135_PIN);

   
    if (mq4 < 0) mq4 = 0;
    if (mq135 < 0) mq135 = 0;

    Serial.printf("Temp: %.2f C, Hum: %.2f%%, MQ4: %d, MQ135: %d\n", temperature, humidity, mq4, mq135);

    lcd.setCursor(0,0);
    lcd.printf("T:%.1fC H:%.1f%%", temperature, humidity);
    lcd.setCursor(0,1);
    lcd.printf("MQ4:%d MQ135:%d", mq4, mq135);


    if (WiFiisConnected()) {
        WiFiClient wifiClient;
        HTTPClient http;

        http.begin(wifiClient, "http://paulkys.local:8000/sensor_data_api/"); 
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<256> doc;
        doc["esp32_id"] = mac_address;
        doc["temperature"] = temperature;
        doc["humidity"] = humidity;
        doc["ch4"] = mq4;
        doc["co2"] = mq135;   
        doc["nox"] = 0;       

        String jsonData;
        serializeJson(doc, jsonData);

        int httpCode = http.POST(jsonData);
        if (httpCode > 0) {
            Serial.println("Data sent successfully");
        } else {
            Serial.println("Error sending data");
        }
        http.end();
    }

    checkLocalThresholds(temperature, humidity, mq4, mq135);


    delay(60000); 
}
