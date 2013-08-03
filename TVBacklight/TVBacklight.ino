/**
 * Arduino sketch to light a WS2812 strip from UDP packets. Intended
 * as an Ambilight like TV backlighting system.
 *
 * Copyright 2013 Daniel Foote.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <Adafruit_NeoPixel.h>

#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>

#define PIN 6

// 604 bytes = 150 pixels + 4 control bytes.
#define PACKET_MAX_SIZE 600

Adafruit_NeoPixel strip = Adafruit_NeoPixel(150, PIN, NEO_GRB + NEO_KHZ800);

// Ethernet variables. Change for your environment.
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
IPAddress ip(10, 0, 14, 200);
unsigned int localPort = 8888;
char packetBuffer[PACKET_MAX_SIZE];
EthernetUDP Udp;

// Internal state variables.
char input = 0;

void setup() {
  // Initialize all pixels to 'off'
  strip.begin();
  strip.show();

  // Set up ethernet.
  Ethernet.begin(mac,ip);
  Udp.begin(localPort);

  // Set up serial hardware.
  Serial.begin(115200);
  Serial.println("Ready.");
}

void loop() {
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    Udp.read(packetBuffer, PACKET_MAX_SIZE);

   if (packetBuffer[0] == 'I') {
     // Input selection command. Change input,
     // and set the colour.
     // The first byte is the input.
     input = packetBuffer[1];

     // And the following four bytes are the colour.
     uint32_t *inputSelectColour = (uint32_t*) &packetBuffer[2];

     for (int i = 0; i < strip.numPixels(); i++ ) {
       strip.setPixelColor(i, *inputSelectColour);
     }
     strip.show();
   }
   if (packetBuffer[0] == 'P') {
     // Pixel data. If it's not for the current input,
     // don't process it.
     // Byte 0: 'P'
     // Byte 1: single byte, input number.
     // Byte 2-3: uint16_t, number of pixels.
     // Byte 3+: pixel data.
     if (packetBuffer[1] == input) {
       uint16_t pixelCount = *((uint16_t*) &packetBuffer[2]);
       uint32_t *pixelColour = (uint32_t*) &packetBuffer[4];

       for (uint16_t i = 0; i < pixelCount; i++) {
         // Prevent internal memory buffer overrun.
         if ((i * 4) < PACKET_MAX_SIZE) {
           strip.setPixelColor(i, *pixelColour);
           pixelColour += 1;
         }
       }
       strip.show();
     }
   }
  }
}
