#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  EEPROM.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import struct
import time
import logging
import smbus2

logger = logging.getLogger(__name__)

# Hardware constants
I2C_BUS      = 1
EEPROM_ADDR  = 0x57
WRITE_DELAY  = 0.012

# Data layout V2 (27 bytes total)
# 0-1   Magic (0x4943)
# 2     Version (2)
# 3     Flags
#         bit0 = auto_brightness
#         bit1 = military_time
#         bit2 = temp_celsius
#         bit3 = globe_push_enabled
# 4     Brightness (current panel)
# 5     Day brightness
# 6     Night brightness
# 7-10  Previous Exchange close (float)
# 11-14 Previous WTI
# 15-18 Previous Brent
# 19-22 Previous Urals
# 23-26 Checksum (uint32)

MAGIC         = 0x4943
VERSION       = 2
VERSION_V1    = 1
BLOCK_SIZE    = 27
BLOCK_SIZE_V1 = 25
STRUCT_FMT    = "<HBBBBBffffI"
STRUCT_FMT_V1 = "<HBBBffffI"

FLAG_AUTO        = 0x01
FLAG_MILITARY    = 0x02
FLAG_CELSIUS     = 0x04
FLAG_GLOBE_PUSH  = 0x08

_DEFAULTS = {
    "auto_brightness":     True,
    "military_time":       True,
    "temp_celsius":        True,
    "brightness":          63,
    "day_brightness":      63,
    "night_brightness":    31,
    "prev_exchange":       0.0,
    "prev_wti":            0.0,
    "prev_brent":          0.0,
    "prev_urals":          0.0,
    "globe_push_enabled":  False,
}

class EEPROM:
    def __init__(self):
        self.available = False
        self.bus = None
        try:
            self.bus = smbus2.SMBus(I2C_BUS)
            self.bus.read_byte(EEPROM_ADDR)
            self.available = True
        except Exception as e:
            logger.warning(f"EEPROM not available: {e}")
            self.available = False

    def _write_byte(self, addr, value):
        self.bus.write_i2c_block_data(
            EEPROM_ADDR,
            (addr >> 8) & 0xFF,
            [addr & 0xFF, value & 0xFF]
        )
        time.sleep(WRITE_DELAY)

    def _read_byte(self, addr):
        self.bus.write_i2c_block_data(
            EEPROM_ADDR,
            (addr >> 8) & 0xFF,
            [addr & 0xFF]
        )
        return self.bus.read_byte(EEPROM_ADDR)

    def _write_block(self, start_addr, data: bytes):
        for i, b in enumerate(data):
            self._write_byte(start_addr + i, b)

    def _read_block(self, start_addr, length) -> bytes:
        result = bytearray()
        for i in range(length):
            result.append(self._read_byte(start_addr + i))
        return bytes(result)

    def _unpack_v2(self, raw):
        (magic, ver, flags, bright, day_b, night_b,
         prev_ex, prev_wti, prev_brent, prev_urals, checksum) = \
            struct.unpack(STRUCT_FMT, raw)
        calc = sum(raw[:-4]) & 0xFFFFFFFF
        if magic != MAGIC or ver != VERSION or checksum != calc:
            return None
        return {
            "auto_brightness":     bool(flags & FLAG_AUTO),
            "military_time":       bool(flags & FLAG_MILITARY),
            "temp_celsius":        bool(flags & FLAG_CELSIUS),
            "globe_push_enabled":  bool(flags & FLAG_GLOBE_PUSH),
            "brightness":          bright,
            "day_brightness":      day_b,
            "night_brightness":    night_b,
            "prev_exchange":       prev_ex,
            "prev_wti":            prev_wti,
            "prev_brent":          prev_brent,
            "prev_urals":          prev_urals,
        }

    def _unpack_v1(self, raw):
        magic, ver, flags, bright, prev_ex, prev_wti, prev_brent, prev_urals, checksum = \
            struct.unpack(STRUCT_FMT_V1, raw)
        calc = sum(raw[:-4]) & 0xFFFFFFFF
        if magic != MAGIC or ver != VERSION_V1 or checksum != calc:
            return None
        return {
            "auto_brightness":     bool(flags & FLAG_AUTO),
            "military_time":       bool(flags & FLAG_MILITARY),
            "temp_celsius":        True,
            "globe_push_enabled":  False,
            "brightness":          bright,
            "day_brightness":      63,
            "night_brightness":    31,
            "prev_exchange":       prev_ex,
            "prev_wti":            prev_wti,
            "prev_brent":          prev_brent,
            "prev_urals":          prev_urals,
        }

    def load(self) -> dict:
        if not self.available:
            return dict(_DEFAULTS)

        try:
            raw = self._read_block(0, BLOCK_SIZE)
            data = self._unpack_v2(raw)
            if data is not None:
                return data

            data = self._unpack_v1(raw[:BLOCK_SIZE_V1])
            if data is not None:
                logger.info("EEPROM v1 migrated to v2")
                self.save(data)
                return data

            logger.warning("EEPROM data invalid or corrupt – using defaults")
            return dict(_DEFAULTS)

        except Exception as e:
            logger.warning(f"EEPROM load failed: {e}")
            return dict(_DEFAULTS)

    def save(self, data: dict):
        if not self.available:
            return False

        try:
            flags = 0
            if data.get("auto_brightness", True):
                flags |= FLAG_AUTO
            if data.get("military_time", True):
                flags |= FLAG_MILITARY
            if data.get("temp_celsius", True):
                flags |= FLAG_CELSIUS
            if data.get("globe_push_enabled", False):
                flags |= FLAG_GLOBE_PUSH

            bright     = int(data.get("brightness", 63)) & 0xFF
            day_b      = int(data.get("day_brightness", 63)) & 0xFF
            night_b    = int(data.get("night_brightness", 31)) & 0xFF
            prev_ex    = float(data.get("prev_exchange", 0.0))
            prev_wti   = float(data.get("prev_wti", 0.0))
            prev_brent = float(data.get("prev_brent", 0.0))
            prev_urals = float(data.get("prev_urals", 0.0))

            body = struct.pack(
                "<HBBBBBffff",
                MAGIC, VERSION, flags, bright, day_b, night_b,
                prev_ex, prev_wti, prev_brent, prev_urals
            )
            checksum = sum(body) & 0xFFFFFFFF
            final = body + struct.pack("<I", checksum)

            self._write_block(0, final)
            return True

        except Exception as e:
            logger.warning(f"EEPROM save failed: {e}")
            return False

eeprom = EEPROM()

def save_persisted():
    from CONFIG import info_center
    with info_center.lock:
        eeprom.save({
            "auto_brightness":    info_center.auto_brightness,
            "military_time":      info_center.military_time,
            "brightness":         info_center.panel_brightness,
            "temp_celsius":       info_center.temp_celsius,
            "day_brightness":     info_center.day_brightness,
            "night_brightness":   info_center.night_brightness,
            "prev_exchange":      info_center.last_exchange_rate,
            "prev_wti":           info_center.prev_wti,
            "prev_brent":         info_center.prev_brent,
            "prev_urals":         info_center.prev_urals,
            "globe_push_enabled": info_center.globe_push_enabled,
        })

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
