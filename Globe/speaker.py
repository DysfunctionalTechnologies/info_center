#----------------------------------------------------------#
#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE_23_LEDs
# Version:    V1.20
# Date:       September 6, 2026
# Module:     speaker.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
# INFO_CENTER_GLOBE — MicroPython / CYD / Thonny
# INFO_CENTER_GLOBE — TFT + 23-LED globe (bitstream, no NeoPixel)
#----------------------------------------------------------#
# GPIO 26, onboard amp, 8 ohm speaker
#----------------------------------------------------------#
#----------------------------------------------------------#

from machine import Pin, PWM
import time

SPK_PIN = 26
_spk = None

def init():
    global _spk
    if _spk is None:
        _spk = PWM(Pin(SPK_PIN), freq=880, duty=0)

def off():
    init()
    _spk.duty(0)

def chirp(freq=880, ms=70, duty=180):
    init()
    _spk.freq(int(freq))
    _spk.duty(int(duty))
    time.sleep_ms(int(ms))
    _spk.duty(0)

def announce(name):
    if name in ("FLASH_RED"):
        chirp(880, 60)
        chirp(440, 90)
    elif name in ("FLASH_YELLOW"):
        chirp(660, 80)
    elif name == "FLASH_RYK":
        chirp(880, 40)
        chirp(660, 40)
        chirp(440, 80)

def self_test():
    chirp(880, 120, 180)
    time.sleep_ms(200)
    chirp(660, 120, 180)
    time.sleep_ms(200)
    chirp(440, 160, 180)
    
def welcome():
    chirp(880, 120, 180)
    time.sleep_ms(200)
    chirp(660, 120, 180)
    time.sleep_ms(200)
    chirp(440, 160, 180)

def wakeup_fanfare():
    chirp(523, 500, 180)    # C5
    chirp(659, 500, 180)    # E5
    chirp(784, 500, 180)    # G5
    chirp(1047, 1000, 220)  # C6

    