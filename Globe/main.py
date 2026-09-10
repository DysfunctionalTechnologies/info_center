#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE
# Module:     main.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#

import json
import time
import network
import socket
import globe
from BOARD import pins

try:
    import secrets
    WIFI_SSID = secrets.WIFI_SSID
    WIFI_PASS = secrets.WIFI_PASS
except Exception:
    WIFI_SSID = ""
    WIFI_PASS = ""

UDP_PORT      = 4210
P             = pins()

FAILSAFE_MS   = 60000 # 60 seconds
HELLO_MS      = 5000  #  5 seconds
BEACON_MS     = 30000 # 30 seconds
WIFI_RETRY_MS = 15000 # 15 seconds

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
    if cmd in ("hello", "here", "ack"):
        return None
    return str(msg.get("mode", "BLUE")).upper()

def _my_ip(wlan):
    try:
        ip = wlan.ifconfig()[0]
        if ip and ip != "0.0.0.0":
            return ip
    except Exception:
        pass
    return ""

wlan = wifi_connect()
globe.wake()
print("wlan", wlan.ifconfig())
print("status", wlan.status())
print("ssid", WIFI_SSID)
print("mode", globe.mode)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
except Exception:
    pass
sock.bind(("0.0.0.0", UDP_PORT))
sock.settimeout(0.05)

last_pkt = time.ticks_ms()
last_hello = time.ticks_add(time.ticks_ms(), -HELLO_MS)
last_wifi = time.ticks_ms()
last_seq = None
last_boot = None
master = None
boot_id = time.ticks_ms() & 0xFFFF
print("INFO_CENTER_GLOBE udp :%d sku %s" % (UDP_PORT, P["SKU"]))

def send_hello(cmd="hello"):
    ip = _my_ip(wlan)
    msg = {
        "v": 1,
        "cmd": cmd,
        "sku": P["SKU"],
        "n": globe.LED_N,
        "boot": boot_id,
        "ip": ip,
        "paired": 1 if master else 0,
    }
    raw = json.dumps(msg).encode("ascii")
    sock.sendto(raw, ("255.255.255.255", UDP_PORT))
    print(cmd, ip, "paired" if master else "single")
    
def send_ack(addr):
    raw = json.dumps({"v": 1, "cmd": "ack"}).encode("ascii")
    try:
        sock.sendto(raw, addr)
        print("ack", addr[0])
    except OSError as e:
        print("ack fail", e)

while True:
    raw = None
    addr = None
    try:
        raw, addr = sock.recvfrom(512)
    except OSError:
        raw = None

    if raw:
        try:
            msg = json.loads(raw)
        except Exception:
            msg = None

        if isinstance(msg, dict):
            cmd = str(msg.get("cmd", "globe")).lower()
            if cmd == "hello":
                pass
            elif cmd == "here":
                if addr:
                    if master and addr[0] != master:
                        print("here ignore", addr[0], "steady", master)
                    else:
                        master = addr[0]
                        globe.set_master(master)
                        send_ack(addr)
                        last_pkt = time.ticks_ms()
                        print("here", master)
            else:
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
                if master and addr and addr[0] != master:
                    stale = True
                if not stale:
                    name = parse_packet(msg)
                    if name:
                        if addr:
                            if master is None:
                                master = addr[0]
                            globe.set_master(addr[0])
                        globe.set_mode(name)
                        globe.set_alerts(msg.get("alerts", []))
                        last_pkt = time.ticks_ms()
                        print(addr, globe.mode, msg.get("alerts", []))

    if not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), last_wifi) >= WIFI_RETRY_MS:
            last_wifi = time.ticks_ms()
            print("wifi retry")
            wlan = wifi_connect()
            print("wlan", wlan.ifconfig(), wlan.status())

    wait = HELLO_MS if master is None else BEACON_MS
    if time.ticks_diff(time.ticks_ms(), last_hello) >= 0:
        last_hello = time.ticks_add(time.ticks_ms(), wait)
        send_hello("hello" if master is None else "beacon")
        
    if time.ticks_diff(time.ticks_ms(), last_pkt) > FAILSAFE_MS:
        last_seq = None
        last_pkt = time.ticks_ms()
        master = None
        globe.set_mode("OFF")
        globe.set_alerts([])

    globe.tick()