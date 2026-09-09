#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
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

GLOBE_HOST    = globe_host()
GLOBE_PORT    = 4210
HEARTBEAT_S   = 2.0
LOCK_EXPIRE_S = 90.0
_seen         = 0.0

_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
_sock.setblocking(False)
try:
    _sock.bind(("0.0.0.0", GLOBE_PORT))
except OSError as e:
    logger.warning("globe listen: %s", e)

_seq       = 0
_last_mode = None
_last_send = 0.0
_BOOT_ID   = os.getpid()
_peer   = globe_host() or GLOBE_HOST
_locked = None

def _poll_hello():
    global _peer, _locked, _seen
    enabled = getattr(info_center, "globe_push_enabled", False)
    if not enabled:
        return
    now = time.monotonic()
    if _locked and (now - _seen) > LOCK_EXPIRE_S:
        logger.info("globe lock expire %s", _locked)
        _locked = None
    try:
        raw, addr = _sock.recvfrom(512)
    except OSError:
        return
    try:
        msg = json.loads(raw.decode("ascii", "ignore"))
    except Exception:
        return
    if not isinstance(msg, dict):
        return
    if str(msg.get("cmd", "")).lower() != "hello":
        return
    src = addr[0]
    if _locked and src != _locked:
        logger.info("globe hello ignore %s locked %s", src, _locked)
        return
    if _locked == src:
        _seen = now
        return
    _locked = src
    _peer = src
    _seen = now
    here = json.dumps({"v": 1, "cmd": "here", "pi": src}).encode("ascii")
    try:
        _sock.sendto(here, addr)
        logger.info("globe here -> %s sku=%s", src, msg.get("sku"))
    except OSError as e:
        logger.warning("globe here: %s", e)
                
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
    _poll_hello()
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
        "n": getattr(info_center, "globe_led_count", 26),
        "seq": _seq,
        "boot": _BOOT_ID,
    }).encode("ascii")
    try:
        dest = _peer or globe_host() or GLOBE_HOST
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
