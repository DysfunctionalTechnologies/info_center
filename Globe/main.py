#----------------------------------------------------------#
#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE_23_LEDs
# Version:    V1.20
# Date:       September 6, 2026
# Module:     main.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
# INFO_CENTER_GLOBE — MicroPython / CYD / Thonny
# INFO_CENTER_GLOBE — TFT + 23-LED globe (bitstream, no NeoPixel)
#----------------------------------------------------------#
#----------------------------------------------------------#

import json
import time
import network
import socket
import globe

try:
    import secrets
    WIFI_SSID = secrets.WIFI_SSID
    WIFI_PASS = secrets.WIFI_PASS
except Exception:
    WIFI_SSID = ""
    WIFI_PASS = ""

UDP_PORT = 4210
FAILSAFE_MS = 60000

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.disconnect()
    except OSError:
        pass
    wlan.active(False)
    time.sleep_ms(300)
    wlan.active(True)
    time.sleep_ms(300)
    if WIFI_SSID and not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                break
            time.sleep_ms(200)
    return wlan

def parse_packet(msg):
    if not isinstance(msg, dict):
        try:
            msg = json.loads(msg)
        except Exception:
            return None
    cmd = str(msg.get("cmd", "globe")).lower()
    if cmd == "off":
        return "OFF"
    return str(msg.get("mode", "BLUE")).upper()

wlan = wifi_connect()
globe.wake()
print("wlan", wlan.ifconfig())
print("status", wlan.status())
print("mode", globe.mode)
print("tft", globe.tft)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))
sock.settimeout(0.05)

last_pkt = time.ticks_ms()
last_seq = None
last_boot = None
print("INFO_CENTER_GLOBE udp :%d" % UDP_PORT)

while True:
    raw = None
    addr = None
    try:
        raw, addr = sock.recvfrom(256)
    except OSError:
        raw = None

    if raw:
        try:
            msg = json.loads(raw)
        except Exception:
            msg = None

        if isinstance(msg, dict):
            stale = False
            boot = msg.get("boot")
            if boot is not None and boot != last_boot:
                last_boot = boot
                last_seq = None

            seq = msg.get("seq")
            if seq is not None:
                try:
                    seq = int(seq) & 0xFFFF
                    if last_seq is not None and ((seq - last_seq) & 0xFFFF) > 0x7FFF:
                        stale = True
                    else:
                        last_seq = seq
                except Exception:
                    stale = True

            if not stale:
                name = parse_packet(msg)
                if name:
                    if addr:
                        globe.set_master(addr[0])
                    globe.set_mode(name)
                    last_pkt = time.ticks_ms()
                    print(addr, globe.mode)
                    
    if time.ticks_diff(time.ticks_ms(), last_pkt) > FAILSAFE_MS:
        last_seq = None
        last_pkt = time.ticks_ms()   # don’t re-enter every loop
        globe.set_mode("OFF")

    globe.tick()
