#----------------------------------------------------------#
#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE_23_LEDs
# Version:    V1.20
# Date:       September 6, 2026
# Module:     globe.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
# INFO_CENTER_GLOBE — MicroPython / CYD / Thonny
# INFO_CENTER_GLOBE — TFT + 23-LED globe (bitstream, no NeoPixel)
#----------------------------------------------------------#
#----------------------------------------------------------#

import time
from   machine import Pin, SoftSPI, bitstream
from   ili9341 import Display, color565
import speaker

LED_PIN = 27
LED_N = 23
USE_LEDS = True
# T0H, T0L, T1H, T1L (ns) — WS2812 800 kHz-ish
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

FLASH_MS = 400
RYK_MS = 350

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

_master_ip = "--"

def set_master(addr):
    global _master_ip
    if addr:
        _master_ip = str(addr).split(":")[0]

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
    global spi, tft
    bl.on()
    if spi is not None:
        try:
            spi.deinit()
        except Exception:
            pass
    spi = SoftSPI(baudrate=20_000_000, polarity=0, phase=0,
                  sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(12))
    tft = Display(spi, dc=Pin(DC_PIN), cs=Pin(CS_PIN), rst=Pin(RST_PIN, Pin.OUT),
                  width=320, height=240, rotation=90)
    _tft_ready = False

def _paint_tft(c):
    global _tft_ready
    if tft is None:
        return
    if not _tft_ready:
        tft.clear(BLACK)
        _tft_ready = True
    try:
        tft.fill_circle(280, 40, 28, c)
    except AttributeError:
        tft.fill_rectangle(252, 12, 56, 56, c)
    _paint_ips()

def _paint_ips():
    if tft is None:
        return
    cyd_line = "CYD " + _cyd_ip()
    pi_line = "PI  " + _master_ip
    print("IPS", cyd_line, pi_line)
    try:
        tft.draw_text8x8(8, 80, cyd_line, WHITE, BLACK)
        tft.draw_text8x8(8, 96, pi_line,  WHITE, BLACK)
    except Exception as e:
        print("TFT text", e)
        
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

def _paint(tft_c, led_c):
    _paint_leds(led_c)
    _paint_tft(tft_c)

def set_mode(name, force=False):
    global mode, _phase, _next
    name = (name or "BLUE").upper()
    if name not in MODES:
        name = "BLUE"
    if name == mode and not force:
        return
    mode = name
    _phase = 0
    _next = time.ticks_ms()
    if mode == "GREEN":
        _paint(GREEN, LED_GREEN)
    elif mode == "YELLOW":
        _paint(YELLOW, LED_YELLOW)
    elif mode == "RED":
        _paint(RED, LED_RED)
    elif mode == "BLUE":
        _paint(BLUE, LED_BLUE)
    elif mode == "OFF":
        _paint(BLACK, LED_BLACK)
    elif mode == "FLASH_RED":
        _paint(RED, LED_RED)
    elif mode == "FLASH_YELLOW":
        _paint(YELLOW, LED_YELLOW)
    elif mode == "FLASH_RYK":
        _paint(RED, LED_RED)
        
    if name not in ("OFF", "BLUE", "GREEN"):
        try:
            speaker.announce(name)
        except Exception:
            pass
        
def wake():
    _init_tft()
    set_mode(mode, force=True)

def tick():
    global _phase, _next
    if mode not in ("FLASH_RED", "FLASH_YELLOW", "FLASH_RYK"):
        return
    now = time.ticks_ms()
    interval = RYK_MS if mode == "FLASH_RYK" else FLASH_MS
    if time.ticks_diff(now, _next) < 0:
        return
    _next = time.ticks_add(now, interval)
    _phase += 1
    if mode == "FLASH_RED":
        on = bool(_phase & 1)
        _paint_leds(LED_RED if on else LED_BLACK)
    elif mode == "FLASH_YELLOW":
        on = bool(_phase & 1)
        _paint_leds(LED_YELLOW if on else LED_BLACK)
    else:
        s = _phase % 3
        _paint_leds(LED_RED if s == 0 else LED_YELLOW if s == 1 else LED_BLACK)
