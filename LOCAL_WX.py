#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  LOCAL_WX.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#
# AHT20 @ 0x38  RH + temperature
# BMP280 @ 0x77 pressure + temperature
#----------------------------------------------------------#

import time
import logging
import smbus2

logger = logging.getLogger(__name__)

I2C_BUS = 1
AHT20_ADDR = 0x38
BMP280_ADDR = 0x77

_bus = None
_bmp_cal = None

def _bus_open():
    global _bus
    if _bus is None:
        _bus = smbus2.SMBus(I2C_BUS)
    return _bus

def _aht20_init():
    bus = _bus_open()
    bus.write_i2c_block_data(AHT20_ADDR, 0xBE, [0x08, 0x00])
    time.sleep(0.02)

def _aht20_read():
    bus = _bus_open()
    bus.write_i2c_block_data(AHT20_ADDR, 0xAC, [0x33, 0x00])
    time.sleep(0.08)
    raw = bus.read_i2c_block_data(AHT20_ADDR, 0x00, 6)
    if raw[0] & 0x80:
        time.sleep(0.08)
        raw = bus.read_i2c_block_data(AHT20_ADDR, 0x00, 6)
    hum_n = ((raw[1] << 12) | (raw[2] << 4) | (raw[3] >> 4)) / 1048576.0
    tmp_n = (((raw[3] & 0x0F) << 16) | (raw[4] << 8) | raw[5]) / 1048576.0
    rh = hum_n * 100.0
    tc = tmp_n * 200.0 - 50.0
    return rh, tc

def _u16le(d, i):
    return d[i] | (d[i + 1] << 8)

def _s16le(d, i):
    v = _u16le(d, i)
    return v - 65536 if v > 32767 else v

def _bmp280_cal():
    global _bmp_cal
    if _bmp_cal is not None:
        return _bmp_cal
    bus = _bus_open()
    d = bus.read_i2c_block_data(BMP280_ADDR, 0x88, 24)
    _bmp_cal = {
        "T1": _u16le(d, 0),
        "T2": _s16le(d, 2),
        "T3": _s16le(d, 4),
        "P1": _u16le(d, 6),
        "P2": _s16le(d, 8),
        "P3": _s16le(d, 10),
        "P4": _s16le(d, 12),
        "P5": _s16le(d, 14),
        "P6": _s16le(d, 16),
        "P7": _s16le(d, 18),
        "P8": _s16le(d, 20),
        "P9": _s16le(d, 22),
    }
    bus.write_byte_data(BMP280_ADDR, 0xF4, 0x27)
    bus.write_byte_data(BMP280_ADDR, 0xF5, 0xA0)
    time.sleep(0.05)
    return _bmp_cal

def _bmp280_read():
    c = _bmp280_cal()
    bus = _bus_open()
    d = bus.read_i2c_block_data(BMP280_ADDR, 0xF7, 6)
    adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
    adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
    tvar1 = (((adc_t >> 3) - (c["T1"] << 1)) * c["T2"]) >> 11
    tvar2 = (((((adc_t >> 4) - c["T1"]) * ((adc_t >> 4) - c["T1"])) >> 12) * c["T3"]) >> 14
    t_fine = tvar1 + tvar2
    tc = ((t_fine * 5 + 128) >> 8) / 100.0
    var1 = t_fine - 128000
    var2 = var1 * var1 * c["P6"]
    var2 = var2 + ((var1 * c["P5"]) << 17)
    var2 = var2 + (c["P4"] << 35)
    var1 = ((var1 * var1 * c["P3"]) >> 8) + ((var1 * c["P2"]) << 12)
    var1 = (((1 << 47) + var1) * c["P1"]) >> 33
    if var1 == 0:
        return None, tc
    p = 1048576 - adc_p
    p = (((p << 31) - var2) * 3125) // var1
    var1 = (c["P9"] * (p >> 13) * (p >> 13)) >> 25
    var2 = (c["P8"] * p) >> 19
    p = ((p + var1 + var2) >> 8) + (c["P7"] << 4)
    hpa = p / 25600.0
    return hpa, tc

def read_local_wx():
    try:
        _aht20_init()
        rh, t_aht = _aht20_read()
    except Exception as e:
        logger.warning("AHT20: %s", e)
        rh, t_aht = None, None
    try:
        hpa, t_bmp = _bmp280_read()
    except Exception as e:
        logger.warning("BMP280: %s", e)
        hpa, t_bmp = None, None
    return {
        "rh": rh,
        "t_aht": t_aht,
        "hpa": hpa,
        "t_bmp": t_bmp,
    }

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    logging.basicConfig(level=logging.INFO)
    print("LOCAL_WX  AHT20@38  BMP280@77  bus1")
    for _ in range(6):
        w = read_local_wx()
        print(
            "RH %.1f%%  T_aht %.2fC  P %.1f hPa  T_bmp %.2fC"
            % (
                w["rh"] if w["rh"] is not None else float("nan"),
                w["t_aht"] if w["t_aht"] is not None else float("nan"),
                w["hpa"] if w["hpa"] is not None else float("nan"),
                w["t_bmp"] if w["t_bmp"] is not None else float("nan"),
            )
        )
        time.sleep(2.0)
#----------------------------------------------------------#
