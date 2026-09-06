INFO_CENTER V1.14
16×32 LED Matrix Information Display for Raspberry Pi
Date: August 29, 2026

A modular wall display: time, date, weather, earthquakes, USD/PHP,
crude oil, internet status, and Pac-Man on a WS281x 16×32 matrix,
plus a 23-LED status globe (wired tail on the Pi and optional
wireless ESP32/CYD on the LAN).


Hardware Requirements
---------------------
• Raspberry Pi 3 or 4 only at this time (GPIO 21 + rpi_ws281x)
• Raspberry Pi 5 is not supported. RP1 broke the old PWM/DMA path;
  a separate SPI/PIO driver would be required.
• 16×32 WS2812B / SK6812 matrix
• 23 additional LEDs for the wired status globe (series after the matrix)
• Optional wireless globe: CYD bench unit or bare ESP32 (UDP :4210)
• DS18B20 1-Wire temperature sensor (optional)
• I2C EEPROM at 0x57 (optional; settings persist without it via defaults)
• 5 V supply for the LEDs — do not power the matrix from the Pi 5 V pin


Default Wiring
--------------
Function          GPIO    Notes
LED Data (DIN)    21      CONFIG.py strip_gpio
DS18B20           4       1-Wire, 4.7 kΩ pull-up
I2C EEPROM        SDA/SCL bus 1, address 0x57

Panel orientation default is 180° (CONFIG.py).

Wireless globe (bench)
• CYD at 192.168.0.43:4210
• Pi GLOBE_LINK.py + push_globe() after update_strip()
• Wired tail stays on the Pi strip; wireless is an extra listener
• Later: bare ESP32 in the globe, 5 V / 2 A jack, same UDP


Software Setup
--------------
1. Enable 1-Wire if using DS18B20
   sudo raspi-config → Interface Options → 1-Wire → Enable

2. Install dependencies
   sudo apt update
   sudo apt install python3-pip python3-rpi.gpio
   sudo pip3 install rpi_ws281x smbus2 flask


Running
-------
  python3 INFO_CENTER.py

Diagnostic menu:
  python3 DIAGNOSTICS.py

Web remote (LAN):
  http://<pi-ip>:5000
  Default login is in WEB.py (move off source before any shared network).


Boot sequence then loop
-----------------------
1  Color wipe (black / red / green / blue / white)
2  Program name
3  Version / copyright
4  Clear upper
5  Clear lower
6+ Repeating lower-panel loop:
     Internet monitor → Pac-Man → Weather → USD/PHP → Oil → Earthquakes

Upper panel (after the loop starts) rotates independently:
  Time → Date → Day-of-week → PH holiday (if today)


Configuration
-------------
CONFIG.py holds constants, geometry, intervals, alert thresholds,
and the info_center singleton (live telemetry + nested pattern state).

EEPROM (25 bytes) stores:
  auto brightness, military time, panel brightness,
  previous exchange / WTI / Brent / Urals.


Features
--------
• Background fetcher thread (weather, USGS quakes, FX, oil, PH holidays)
• Auto day/night brightness from Open-Meteo is_day (clock fallback)
• Software watchdog (20 s) + Flask remote on port 5000
• Alerts: globe FLASH_RED / FLASH_YELLOW / FLASH_RYK
• Border colour follows internet status
• Dual globe: wired NeoPixel tail + UDP wireless (same seven modes)


Project Structure
-----------------
CONFIG.py          Settings + info_center singleton
PANEL.py           WS281x, drawing, border, wired globe
DISPLAY.py         Upper panel + holiday scroll
INFO_CENTER.py     Main loop and pattern table
DATA_FETCHER.py    Background API polling
GLOBE_LINK.py      UDP push to wireless globe

EARTHQUAKE.py      Quake ticker
EXCHANGE.py        USD/PHP + arrows + dissolve
OIL.py             WTI / Brent / Urals
WEATHER.py         Indoor + outdoor weather scroll
PACMAN.py          Chase animation
IMONITOR.py        INTERNET letter pings

WEB.py             Flask remote
EEPROM.py          I2C persist
DIAGNOSTICS.py     Hardware tests
TEMPERATURE.py     DS18B20 (45 s cache)
INDICATORS.py      Colon, AM/PM, military, date slashes
FONT_3X6.py        3×6 font + arrow / sun / moon glyphs


Notes
-----
• User-Agent is built from info_center.version_string in CONFIG.py.
• Oil endpoint is a demo API; treat empty/fail as OIL OFFLINE and do
  not persist zeros over real previous closes.
• First paint of a data pattern may show OFFLINE until the fetcher
  returns.
• /status on the web UI is currently unauthenticated on the LAN.
• Wireless globe: LAN-only UDP. Router down → wireless failsafe BLUE
  after 60 s; “no master” is not the same as WAN down.
• Pi 5 support (detect board, SPI on GPIO 10 or RP1 PIO, same PANEL
  API) is deferred.
