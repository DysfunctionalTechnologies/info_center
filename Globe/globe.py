#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE_23_LEDs
# Version:    V1.20
# Date:       September 6, 2026
# Module:     globe.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#

import time
from   machine import Pin, SoftSPI, bitstream
from   ili9341 import Display, color565
import speaker

LED_PIN = 27
LED_N = 23
USE_LEDS = True
LED_TIMING = (400, 850, 800, 450)

BL_PIN = 21
CS_PIN = 15
DC_PIN = 2
RST_PIN = 4
SCK_PIN = 14
MOSI_PIN = 13

RED = color565(255, 0, 0)
YELLOW = color565(255, 180, 0)
GREEN = color565(0, 255, 0)
BLUE = color565(0, 0, 255)
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)

LED_RED = (255, 0, 0)
LED_YELLOW = (255, 180, 0)
LED_GREEN = (0, 255, 0)
LED_BLUE = (0, 40, 255)
LED_BLACK = (0, 0, 0)

FLASH_MS = 500
RYK_MS = 500

MODES = {
    "GREEN", "YELLOW", "RED", "BLUE",
    "FLASH_RED", "FLASH_YELLOW", "FLASH_RYK", "OFF",
}

bl = Pin(BL_PIN, Pin.OUT)
bl.on()
led_pin = Pin(LED_PIN, Pin.OUT)
led_pin.value(0)

spi = None
tft = None
_tft_ready = False
mode = "BLUE"
_phase = 0
_next = time.ticks_ms()
_pending_mode = None
_master_ip = "--"
_net_line = ("INTERNET UNTESTED", BLUE)
_alert_line = ("", BLACK)
_items = []
_slots = {
    ("WX", "Y"): "",
    ("WX", "R"): "",
    ("QK", "Y"): "",
    ("QK", "R"): "",
    ("FX", "Y"): "",
    ("FX", "R"): "",
    ("ST", "Y"): "",
    ("ST", "R"): "",
}

SLOT_CHARS = 10
SLOT_PAD = "          "
def set_master(addr):
    global _master_ip
    if addr:
        _master_ip = str(addr).split(":")[0]

def set_alerts(raw):
    global _items
    out = []
    if isinstance(raw, list):
        for it in raw:
            if isinstance(it, dict):
                g = str(it.get("g", "")).upper()
                s = str(it.get("s", "")).strip().upper()
                b = str(it.get("c", "Y")).upper()[:1]
                if b not in ("Y", "R"):
                    b = "Y"
                if g and s:
                    out.append((g, s, b))
    if out == _items:
        return
    _items = out
    if tft is not None:
        _paint_status()
        
def _cyd_ip():
    try:
        import network
        w = network.WLAN(network.STA_IF)
        ip = w.ifconfig()[0] if w.isconnected() else ""
        if ip and ip != "0.0.0.0":
            return ip
    except Exception:
        pass
    return "--"

def _init_tft():
    global spi, tft, _tft_ready
    print("TFT init start")
    bl.on()
    if spi is not None:
        try:
            spi.deinit()
        except Exception as e:
            print("TFT spi deinit", e)
        spi = None
    try:
        spi = SoftSPI(
            baudrate=20_000_000,
            polarity=0,
            phase=0,
            sck=Pin(SCK_PIN),
            mosi=Pin(MOSI_PIN),
            miso=Pin(12),
        )
        tft = Display(
            spi,
            dc=Pin(DC_PIN),
            cs=Pin(CS_PIN),
            rst=Pin(RST_PIN, Pin.OUT),
            width=320,
            height=240,
            rotation=90,
        )
        _tft_ready = False
        print("TFT display ok", tft)
    except Exception as e:
        tft = None
        _tft_ready = False
        print("TFT init FAIL", e)

def _cycle_len(m):
    if m == "FLASH_RYK":
        return 3
    if m in ("FLASH_RED", "FLASH_YELLOW"):
        return 2
    return 1

def _paint_leds(rgb):
    if not USE_LEDS:
        return
    r, g, b = rgb
    buf = bytearray(LED_N * 3)
    for i in range(LED_N):
        buf[i * 3] = g
        buf[i * 3 + 1] = r
        buf[i * 3 + 2] = b
    bitstream(led_pin, 0, LED_TIMING, buf)

def _update_status_from_mode(name):
    global _net_line, _alert_line, _items
    if name == "GREEN":
        _net_line = ("INTERNET GOOD", GREEN)
        _alert_line = ("", BLACK)
        _items = []
    elif name == "YELLOW":
        _net_line = ("INTERNET ISSUES", YELLOW)
        _alert_line = ("", BLACK)
        _items = []
    elif name == "RED":
        _net_line = ("INTERNET DOWN", RED)
        _alert_line = ("", BLACK)
        _items = []
    elif name == "BLUE":
        _net_line = ("INTERNET UNTESTED", BLUE)
        _alert_line = ("", BLACK)
        _items = []
    elif name == "OFF":
        _net_line = ("", BLACK)
        _alert_line = ("", BLACK)
        _items = []
    elif name == "FLASH_YELLOW":
        _alert_line = ("ALERT YELLOW", YELLOW)
    elif name == "FLASH_RED":
        _alert_line = ("ALERT RED", RED)
    elif name == "FLASH_RYK":
        _alert_line = ("ALERT RED/YELLOW", RED)

def _leds_for_mode(name, step=0):
    if name == "GREEN":
        return LED_GREEN
    if name == "YELLOW":
        return LED_YELLOW
    if name == "RED":
        return LED_RED
    if name == "BLUE":
        return LED_BLUE
    if name == "OFF":
        return LED_BLACK
    if name == "FLASH_RED":
        return LED_RED if step == 0 else LED_BLACK
    if name == "FLASH_YELLOW":
        return LED_YELLOW if step == 0 else LED_BLACK
    if name == "FLASH_RYK":
        if step == 0:
            return LED_RED
        if step == 1:
            return LED_YELLOW
        return LED_BLACK
    return LED_BLUE

def _slot_word(group, band):
    for g, s, b in _items:
        if g == group and b == band:
            return s
    return ""

def _paint_slot(y, col, group, band, color):
    key = (group, band)
    new = _slot_word(group, band)
    old = _slots.get(key, "")
    if new == old:
        return
    x = 8 + col * 8
    if new:
        tft.draw_text8x8(x, y, (new + SLOT_PAD)[:SLOT_CHARS], color, BLACK)
    else:
        tft.draw_text8x8(x, y, SLOT_PAD, BLACK, BLACK)
    _slots[key] = new

def _paint_group(y, group):
    _paint_slot(y, 0,  group, "Y", YELLOW)
    _paint_slot(y, 10, group, "R", RED)
    
def _paint_status():
    global _tft_ready
    if tft is None:
        print("TFT none, retry init")
        _init_tft()
    if tft is None:
        print("TFT still none")
        return
    try:
        if not _tft_ready:
            tft.clear(BLACK)
            _tft_ready = True
        cyd_line = "CYD " + _cyd_ip()
        pi_line  = "PI  " + _master_ip
        net_s = (_net_line[0] + "                    ")[:20]
        al_s  = (_alert_line[0] + "                    ")[:20]
        tft.draw_text8x8(8, 16, cyd_line, WHITE, BLACK)
        tft.draw_text8x8(8, 32, pi_line,  WHITE, BLACK)
        tft.draw_text8x8(8, 56, net_s, _net_line[1], BLACK)
        tft.draw_text8x8(8, 72, al_s,  _alert_line[1], BLACK)
        _paint_group(88,  "WX")
        _paint_group(104, "QK")
        _paint_group(120, "FX")
        _paint_group(136, "ST")
        print("TFT", cyd_line, pi_line, net_s.strip(), al_s.strip(), _items)
    except Exception as e:
        print("TFT text", e)

def _apply_mode(name):
    global mode, _phase, _next, _pending_mode
    mode = name
    _pending_mode = None
    _phase = 0
    _next = time.ticks_ms()
    _update_status_from_mode(name)
    _paint_leds(_leds_for_mode(name, 0))
    _paint_status()
    if name.startswith("FLASH"):
        try:
            speaker.announce(name)
        except Exception:
            pass

def set_mode(name, force=False):
    global _pending_mode
    name = (name or "BLUE").upper()
    if name not in MODES:
        name = "BLUE"
    if name == mode and not force:
        _pending_mode = None
        return
    if (not force) and mode.startswith("FLASH") and _cycle_len(mode) > 1:
        _pending_mode = name
        return
    _apply_mode(name)

def wake():
    print("wake")
    _init_tft()
    print("wake tft", tft)
    set_mode(mode, force=True)

def tick():
    global _phase, _next
    if mode not in ("FLASH_RED", "FLASH_YELLOW", "FLASH_RYK"):
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, _next) < 0:
        return
    interval = RYK_MS if mode == "FLASH_RYK" else FLASH_MS
    _next = time.ticks_add(now, interval)
    _phase += 1
    n = _cycle_len(mode)
    step = _phase % n
    _paint_leds(_leds_for_mode(mode, step))
    if step == 0 and _pending_mode is not None:
        _apply_mode(_pending_mode)