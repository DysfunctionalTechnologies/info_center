#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 6, 2026
# Module:  GLOBE_LINK.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import json
import logging
import socket
import time
import os

# Project Imports
from CONFIG   import info_center
from CONFIG   import NETWORK_GOOD, NETWORK_PROBLEM, NETWORK_BAD
from PLATFORM import globe_host

logger = logging.getLogger(__name__)

GLOBE_HOST  = globe_host()
GLOBE_PORT  = 4210
HEARTBEAT_S = 2.0

_sock      = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_sock.setblocking(False)
_seq       = 0
_last_mode = None
_last_send = 0.0
_BOOT_ID   = os.getpid()

def current_globe_mode():
    now = time.monotonic()
    high = now < getattr(info_center, "alert_high_until", 0.0)
    low  = now < getattr(info_center, "alert_low_until", 0.0)
    if high and low:
        return "FLASH_RYK"
    if high or (info_center.alert_level == 2 and now < info_center.alert_until):
        return "FLASH_RED"
    if low or (info_center.alert_level == 1 and now < info_center.alert_until):
        return "FLASH_YELLOW"
    inet = info_center.internet_status
    if inet == NETWORK_GOOD:
        return "GREEN"
    if inet == NETWORK_PROBLEM:
        return "YELLOW"
    if inet == NETWORK_BAD:
        return "RED"
    return "BLUE"

def push_globe(force=False, mode=None):
    global _seq, _last_mode, _last_send
    enabled = getattr(info_center, "globe_push_enabled", False)
    if mode is None:
        if not enabled:
            return
        mode = current_globe_mode()
    now = time.monotonic()
    if not force and mode == _last_mode and (now - _last_send) < HEARTBEAT_S:
        return
    _seq = (_seq + 1) & 0xFFFF
    if str(mode).startswith("FLASH"):
        items = list(getattr(info_center, "alert_items", []) or [])
    else:
        items = []
        info_center.alert_items = []
        info_center.alert_nouns = []
    why = [{"g": g, "s": t, "c": c} for (g, t, c) in items]
    payload = json.dumps({
        "v": 1,
        "cmd": "globe",
        "mode": mode,
        "alerts": why,
        "n": getattr(info_center, "globe_led_count", 23),
        "seq": _seq,
        "boot": _BOOT_ID,
    }).encode("ascii")
    try:
        dest = globe_host() or GLOBE_HOST
        _sock.sendto(payload, (dest, GLOBE_PORT))
        _last_mode = mode
        _last_send = now
    except OSError as e:
        logger.warning("globe udp: %s", e)

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
