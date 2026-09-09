#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE
# Module:     globe.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#

import time
from   machine import Pin, bitstream
from   BOARD   import pins
import speaker

P = pins()

LED_PIN = P["LED_PIN"]
RING_N = int(P["LED_N"])
GLANCE_N = int(P["GLANCE_N"])
LED_N = RING_N + GLANCE_N
USE_LEDS = P["USE_LEDS"]
USE_TFT = P["USE_TFT"]
LED_TIMING = (400, 850, 800, 450)

# Glance pixels are RING_N .. RING_N+GLANCE_N-1 (15-20 on S3ZERO, 20-25 on CYD/S3DEV)
GLANCE_LABELS = (None, "OL", "ST", "FX", "QK", "WX")

if USE_TFT:
    from machine import SoftSPI
    from ili9341 import Display, color565
    BL_PIN   = P["BL_PIN"]
    CS_PIN   = P["CS_PIN"]
    DC_PIN   = P["DC_PIN"]
    RST_PIN  = P["RST_PIN"]
    SCK_PIN  = P["SCK_PIN"]
    MOSI_PIN = P["MOSI_PIN"]
    MISO_PIN = P["MISO_PIN"]
else:
    def color565(*_a):
        return 0
    BL_PIN = CS_PIN = DC_PIN = RST_PIN = None
    SCK_PIN = MOSI_PIN = MISO_PIN = None

TEXT_BLACK  = color565(  0,   0,   0)
TEXT_RED    = color565(255,   0,   0)
TEXT_YELLOW = color565(255, 255,   0)
TEXT_GREEN  = color565(  0, 255,   0)
TEXT_CYAN   = color565(  0, 255, 255)
TEXT_BLUE   = color565(  0,   0, 255)
TEXT_PURPLE = color565(255,   0, 255)
TEXT_WHITE  = color565(255, 255, 255)

LED_BRIGHTNESS = 31
LED_BLACK   = (             0,              0,              0)
LED_RED     = (LED_BRIGHTNESS,              0,              0)
LED_YELLOW  = (LED_BRIGHTNESS, LED_BRIGHTNESS,              0)
LED_GREEN   = (             0, LED_BRIGHTNESS,              0)
LED_CYAN    = (             0, LED_BRIGHTNESS, LED_BRIGHTNESS)
LED_BLUE    = (             0,              0, LED_BRIGHTNESS)
LED_PURPLE  = (LED_BRIGHTNESS,              0, LED_BRIGHTNESS)
LED_WHITE   = (LED_BRIGHTNESS, LED_BRIGHTNESS, LED_BRIGHTNESS)

FLASH_MS = 1000
RYK_MS   = 666

MODES = {
    "GREEN", "YELLOW", "RED", "BLUE",
    "FLASH_RED", "FLASH_YELLOW", "FLASH_RYK", "OFF",
}

RYK_GROUPS = ("WX", "QK")

bl = None
if USE_TFT and BL_PIN is not None:
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
_net_line = ("INTERNET UNTESTED", TEXT_BLUE)
_alert_line = ("", TEXT_BLACK)
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
    if USE_TFT and tft is not None:
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
    if not USE_TFT:
        tft = None
        _tft_ready = False
        return
    print("TFT init start")
    if bl is not None:
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
            miso=Pin(MISO_PIN),
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

def _item_band(group):
    if not group:
        return ""
    got_r = False
    got_y = False
    for g, s, b in _items:
        if g != group:
            continue
        if b == "R":
            got_r = True
        elif b == "Y":
            got_y = True
    if group in RYK_GROUPS:
        if got_r and got_y:
            return "RYK"
        if got_r:
            return "R"
        if got_y:
            return "Y"
        return ""
    if got_r:
        return "R"
    if got_y:
        return "Y"
    return ""

def _flash_rgb(band, step):
    if band == "RYK":
        k = step % 3
        if k == 0:
            return LED_RED
        if k == 1:
            return LED_YELLOW
        return LED_BLACK
    if band == "R":
        return LED_RED if (step % 2) == 0 else LED_BLACK
    if band == "Y":
        return LED_YELLOW if (step % 2) == 0 else LED_BLACK
    return LED_BLACK

def _glance_group(idx):
    g = idx - RING_N
    if 0 <= g < len(GLANCE_LABELS):
        return GLANCE_LABELS[g]
    return None

def _glance_rgb(idx, step):
    return _flash_rgb(_item_band(_glance_group(idx)), step)

def _paint_leds(rgb, step=0):
    if not USE_LEDS:
        return
    r, g, b = rgb
    buf = bytearray(LED_N * 3)
    ring = RING_N if RING_N <= LED_N else LED_N
    for i in range(ring):
        buf[i * 3] = g
        buf[i * 3 + 1] = r
        buf[i * 3 + 2] = b
    for i in range(ring, LED_N):
        gr, gg, gb = _glance_rgb(i, step)
        buf[i * 3] = gg
        buf[i * 3 + 1] = gr
        buf[i * 3 + 2] = gb
    bitstream(led_pin, 0, LED_TIMING, buf)

def black():
    _paint_leds(LED_BLACK, 0)

def _update_status_from_mode(name):
    global _net_line, _alert_line, _items
    if name == "GREEN":
        _net_line = ("INTERNET GOOD", TEXT_GREEN)
        _alert_line = ("", TEXT_BLACK)
        _items = []
    elif name == "YELLOW":
        _net_line = ("INTERNET ISSUES", TEXT_YELLOW)
        _alert_line = ("", TEXT_BLACK)
        _items = []
    elif name == "RED":
        _net_line = ("INTERNET DOWN", TEXT_RED)
        _alert_line = ("", TEXT_BLACK)
        _items = []
    elif name == "BLUE":
        _net_line = ("INTERNET UNTESTED", TEXT_BLUE)
        _alert_line = ("", TEXT_BLACK)
        _items = []
    elif name == "OFF":
        _net_line = ("", TEXT_BLACK)
        _alert_line = ("", TEXT_BLACK)
        _items = []
    elif name == "FLASH_YELLOW":
        _alert_line = ("ALERT YELLOW", TEXT_YELLOW)
    elif name == "FLASH_RED":
        _alert_line = ("ALERT RED", TEXT_RED)
    elif name == "FLASH_RYK":
        _alert_line = ("ALERT RED/YELLOW", TEXT_RED)

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
    if tft is None:
        return
    key = (group, band)
    new = _slot_word(group, band)
    old = _slots.get(key, "")
    if new == old:
        return
    x = 8 + col * 8
    if new:
        tft.draw_text8x8(x, y, (new + SLOT_PAD)[:SLOT_CHARS], color, TEXT_BLACK)
    else:
        tft.draw_text8x8(x, y, SLOT_PAD, TEXT_BLACK, TEXT_BLACK)
    _slots[key] = new

def _paint_group(y, group):
    _paint_slot(y, 0,  group, "Y", TEXT_YELLOW)
    _paint_slot(y, 10, group, "R", TEXT_RED)

def _paint_status():
    global _tft_ready
    if not USE_TFT:
        return
    if tft is None:
        print("TFT none, retry init")
        _init_tft()
    if tft is None:
        print("TFT still none")
        return
    try:
        if not _tft_ready:
            tft.clear(TEXT_BLACK)
            _tft_ready = True
        cyd_line = "CYD " + _cyd_ip()
        pi_line  = "PI  " + _master_ip
        net_s = (_net_line[0] + "                    ")[:20]
        al_s  = (_alert_line[0] + "                    ")[:20]
        tft.draw_text8x8(8, 16, cyd_line, TEXT_WHITE, TEXT_BLACK)
        tft.draw_text8x8(8, 32, pi_line,  TEXT_WHITE, TEXT_BLACK)
        tft.draw_text8x8(8, 56, net_s, _net_line[1], TEXT_BLACK)
        tft.draw_text8x8(8, 72, al_s,  _alert_line[1], TEXT_BLACK)
        _paint_group(88,  "WX")
        _paint_group(104, "QK")
        _paint_group(120, "FX")
        _paint_group(136, "ST")
        print("TFT", cyd_line, pi_line, net_s.strip(), al_s.strip(), _items)
    except Exception as e:
        print("TFT text", e)

def _glance_busy():
    for group in GLANCE_LABELS:
        if _item_band(group):
            return True
    return False

def _apply_mode(name):
    global mode, _phase, _next, _pending_mode
    mode = name
    _pending_mode = None
    _phase = 0
    _next = time.ticks_ms()
    _update_status_from_mode(name)
    _paint_leds(_leds_for_mode(name, 0), 0)
    _paint_status()
    if name.startswith("FLASH") and P["USE_SPEAKER"]:
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
    print("wake", P["SKU"], "led", LED_PIN, "n", LED_N, "ring", RING_N)
    _init_tft()
    set_mode(mode, force=True)

def tick():
    global _phase, _next
    flashing = mode in ("FLASH_RED", "FLASH_YELLOW", "FLASH_RYK")
    if not flashing and not _glance_busy():
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, _next) < 0:
        return
    interval = RYK_MS if mode == "FLASH_RYK" else FLASH_MS
    _next = time.ticks_add(now, interval)
    _phase += 1
    n = _cycle_len(mode)
    gstep = _phase % n if flashing else 0
    _paint_leds(_leds_for_mode(mode, gstep), _phase)
    if flashing and gstep == 0 and _pending_mode is not None:
        _apply_mode(_pending_mode)

black()

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run main.py")
#----------------------------------------------------------#