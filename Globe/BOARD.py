#----------------------------------------------------------#
# Project:    Info_Center_16x32
# Subproject: Info_Center_GLOBE
# Module:     BOARD.py
# Author:     Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#

VERSION = "V1.21"
SKU     = "CYD"     # "CYD" or "S3DEV"

_CYD    = {
    "SKU":         "CYD",
    "LED_PIN":     27,
    "LED_N":       20,
    "GLANCE_N":    6,
    "RGB_PIN":     None,
    "USE_LEDS":    True,
    "USE_TFT":     True,
    "USE_SPEAKER": True,
    "SPK_PIN":     26,
    "BL_PIN":      21,
    "CS_PIN":      15,
    "DC_PIN":      2,
    "RST_PIN":     4,
    "SCK_PIN":     14,
    "MOSI_PIN":    13,
    "MISO_PIN":    12,
}

_S3DEV  = {
    "SKU":         "S3DEV",
    "LED_PIN":     47,
    "LED_N":       20,
    "GLANCE_N":    6,
    "RGB_PIN":     48,
    "USE_LEDS":    True,
    "USE_TFT":     False,
    "USE_SPEAKER": False,
    "SPK_PIN":     None,
    "BL_PIN":      None,
    "CS_PIN":      None,
    "DC_PIN":      None,
    "RST_PIN":     None,
    "SCK_PIN":     None,
    "MOSI_PIN":    None,
    "MISO_PIN":    None,
}

_TABLE  = {"CYD": _CYD, "S3DEV": _S3DEV}

def pins():
    return dict(_TABLE.get(SKU, _CYD))

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run main.py on the globe board.")
#----------------------------------------------------------#