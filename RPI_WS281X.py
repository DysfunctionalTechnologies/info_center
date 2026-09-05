#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 5, 2026
# Module:  RPI_WS281X.py
# Author:  Grok AI with Timothy S. Carlson spectating
#----------------------------------------------------------#
#----------------------------------------------------------#
# Pi 4-: rpi_ws281x PWM/PCM/DMA
# Pi 5:  RP1 PIO via ws281x_pio.so (GPIO 21 OK)
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import os
import logging
import ctypes

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_SO   = os.path.join(_HERE, "ws281x_pio.so")

def read_model():
    for path in ("/proc/device-tree/model",
                 "/sys/firmware/devicetree/base/model"):
        try:
            raw = open(path, "rb").read().split(b"\x00", 1)[0]
            return raw.decode("ascii", "replace").strip()
        except OSError:
            continue
    return "unknown"

def is_pi5(model=None):
    return "raspberry pi 5" in (model or read_model()).lower()

class _BaseStrip:
    def begin(self):
        return None

    def numPixels(self):
        return self._count

    def setPixelColor(self, index, color):
        if 0 <= index < self._count:
            self._pixels[index] = int(color) & 0xFFFFFF

    def getPixelColor(self, index):
        if 0 <= index < self._count:
            return self._pixels[index]
        return 0

    def _cleanup(self):
        try:
            for i in range(self._count):
                self.setPixelColor(i, 0)
            self.show()
        except Exception:
            pass

class PwmDmaStrip(_BaseStrip):
    def __init__(self, count, gpio, freq, dma, invert, brightness, channel):
        from rpi_ws281x import Adafruit_NeoPixel
        self._count = int(count)
        self._pixels = [0] * self._count
        self._hw = Adafruit_NeoPixel(
            self._count, gpio, freq, dma, invert, brightness, channel
        )
        self.backend = "pwm_dma"
        self.gpio = gpio

    def begin(self):
        self._hw.begin()

    def setPixelColor(self, index, color):
        super().setPixelColor(index, color)
        self._hw.setPixelColor(index, color)

    def show(self):
        self._hw.show()

    def _cleanup(self):
        try:
            for i in range(self._count):
                self._hw.setPixelColor(i, 0)
            self._hw.show()
        except Exception:
            pass
        if hasattr(self._hw, "_cleanup"):
            try:
                self._hw._cleanup()
            except Exception:
                pass

class PioStrip(_BaseStrip):
    _lib = None

    @classmethod
    def _load(cls):
        if cls._lib is not None:
            return cls._lib
        if not os.path.isfile(_SO):
            raise RuntimeError("missing " + _SO)
        lib = ctypes.CDLL(_SO)
        lib.ws_init.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.ws_init.restype = ctypes.c_int
        lib.ws_set.argtypes = [ctypes.c_int, ctypes.c_uint32]
        lib.ws_show.restype = ctypes.c_int
        lib.ws_close.restype = None
        cls._lib = lib
        return lib

    def __init__(self, count, gpio, freq=800000, brightness=31):
        lib = self._load()
        if lib.ws_init(int(gpio), int(count)) != 0:
            raise RuntimeError("PIO ws_init failed (gpio=%s n=%s)" % (gpio, count))
        self._count = int(count)
        self._pixels = [0] * self._count
        self._lib = lib
        self.backend = "pio"
        self.gpio = int(gpio)
        self._hw_brightness = max(0, min(255, int(brightness)))
        
    def setPixelColor(self, index, color):
        color = int(color) & 0xFFFFFF
        super().setPixelColor(index, color)
        scale = self._hw_brightness
        if scale < 255:
            def _dim(ch):
                if ch <= 0 or scale <= 0:
                    return 0
                out = (ch * scale + 127) // 255
                return out if out else 1
            r = _dim((color >> 16) & 0xFF)
            g = _dim((color >> 8) & 0xFF)
            b = _dim(color & 0xFF)
            color = (r << 16) | (g << 8) | b
        self._lib.ws_set(int(index), color)
                
    def show(self):
        if self._lib.ws_show() != 0:
            raise RuntimeError("PIO ws_show failed")

    def _cleanup(self):
        try:
            self._lib.ws_close()
        except Exception:
            pass

def create_strip(count, gpio=21, freq=800000, dma=10,
                 invert=False, brightness=255, channel=0,
                 force=None):
    model = read_model()
    use_pio = (force == "pio") or (force is None and is_pi5(model))
    if force == "pwm":
        use_pio = False
    logger.info("WS281x host=%s pio=%s gpio=%s n=%s",
                model, use_pio, gpio, count)
    if use_pio:
        return PioStrip(count, gpio, freq=freq, brightness=brightness)
    return PwmDmaStrip(count, gpio, freq, dma, invert, brightness, channel)
    
#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
