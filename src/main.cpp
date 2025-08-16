#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "DHT.h"

#define DHTTYPE DHT22 
//DEFINING PINS
#define DHTPIN 18                        
#define ledRedPin 33         
#define ledGreenPin 27 
#define ledOrangePin 5 
DHT dht(DHTPIN, DHTTYPE);


//humidity and Temperature

// lcd 
LiquidCrystal_I2C lcd(0x27, 16, 2);

// wifi CONNECTIVITY
const char* ssid = "EMAGREENHOUSE";
const char* password = "greenhouse2025";
void WiFiconnect() {
    unsigned long startTime = millis();
    Serial.println("Connecting to WiFi...");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 3) {
        delay(10000);
        Serial.print("IP Address");
        lcd.setCursor(0,0);
        lcd.print("WIFI CONNECTED");
        attempts++;
    }
    unsigned long endTime = millis(); 
    unsigned long duration = endTime - startTime;  

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\nFailed to connect! Restarting...");
        lcd.setCursor(0,0);
        lcd.print("WiFi Failed!");
        WiFi.disconnect(true);
    } else {
        Serial.printf("\nConnected! IP: %s\n", WiFi.localIP());
        Serial.printf("Time taken to connect: %lu milliseconds\n", duration);
    }
}

bool WiFiisConnected() {
    return WiFi.status() == WL_CONNECTED;
}

void WiFicheckConnection() {
    if (!WiFiisConnected()) {
        Serial.println("WIFI IS NOT CONNECTED ");
        digitalWrite(ledGreenPin, 0);
        digitalWrite(ledRedPin, 1);
        Serial.println("WiFi lost! Reconnecting...");
        WiFiconnect();
    }else{
        Serial.println("WIFI IS CONNECTED ");
        digitalWrite(ledRedPin, 0);
        digitalWrite(ledGreenPin, 1);
        Serial.println("WIFI IS CONNECTED AND GREEN LED ON ");
    }
}


void setup() {
     Serial.begin(115200);   
     delay(2000); 
     // DIODES
      pinMode(ledRedPin, OUTPUT);
      pinMode(ledGreenPin, OUTPUT);
      pinMode(ledOrangePin, OUTPUT);

      WiFiconnect();
       dht.begin();

      // lcd 
      lcd.init();
      lcd.backlight(); 
      lcd.setCursor(0,0);
      lcd.print("Connecting WiFi");
}

void loop() {
 
    WiFicheckConnection();
     float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // Check if any reads failed
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    lcd.setCursor(0,0);
    lcd.print("DHT Read Error  ");
  } else {
    // Print to Serial
    Serial.print("Humidity: "); Serial.print(humidity); Serial.print("%  ");
    Serial.print("Temperature: "); Serial.print(temperature); Serial.println("°C");

    // Print to LCD
    lcd.setCursor(0,0);
    lcd.print("Temp: "); lcd.print(temperature); lcd.print(" C ");
    lcd.setCursor(0,1);
    lcd.print("Hum: "); lcd.print(humidity); lcd.print("%      ");
  }

  delay(2000); // Wait 2 seconds between readings
}
