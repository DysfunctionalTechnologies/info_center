#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  PLATFORM.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import os

logger = logging.getLogger(__name__)

PLATFORM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".platform")

DEFAULTS = {
    "PANEL_LAYOUT": "16x16",
    "GPIO_PIN": "21",
    "GLOBE_PUSH": "0",
    "GLOBE_HOST": "192.168.0.223",
    "DIAG_BRIGHTNESS": "",
    "DISPLAY_NAME": "",
}

ALLOWED_LAYOUTS = ("16x16", "8x32")


def _truthy(val):
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _parse(text):
    out = dict(DEFAULTS)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().upper()
        if key in DEFAULTS:
            out[key] = val.strip()
    return out


def _validate(data):
    clean = dict(DEFAULTS)
    clean.update(data)

    layout = clean.get("PANEL_LAYOUT", DEFAULTS["PANEL_LAYOUT"]).strip()
    if layout not in ALLOWED_LAYOUTS:
        layout = DEFAULTS["PANEL_LAYOUT"]
    clean["PANEL_LAYOUT"] = layout

    try:
        pin = int(str(clean.get("GPIO_PIN", DEFAULTS["GPIO_PIN"])).strip())
        if pin < 0 or pin > 27:
            pin = int(DEFAULTS["GPIO_PIN"])
    except (TypeError, ValueError):
        pin = int(DEFAULTS["GPIO_PIN"])
    clean["GPIO_PIN"] = str(pin)

    clean["GLOBE_PUSH"] = "1" if _truthy(clean.get("GLOBE_PUSH", "0")) else "0"
    clean["GLOBE_HOST"] = str(clean.get("GLOBE_HOST", DEFAULTS["GLOBE_HOST"])).strip() or DEFAULTS["GLOBE_HOST"]
    clean["DIAG_BRIGHTNESS"] = str(clean.get("DIAG_BRIGHTNESS", "")).strip()
    clean["DISPLAY_NAME"] = str(clean.get("DISPLAY_NAME", "")).strip()
    return clean


def load_platform():
    """Return (cfg_dict, file_present)."""
    if not os.path.isfile(PLATFORM_PATH):
        return _validate(dict(DEFAULTS)), False
    try:
        with open(PLATFORM_PATH, "r", encoding="utf-8") as handle:
            parsed = _parse(handle.read())
        return _validate(parsed), True
    except OSError:
        return _validate(dict(DEFAULTS)), False


def save_platform(fields):
    current, _ = load_platform()
    if fields:
        for key, val in fields.items():
            key_u = str(key).strip().upper()
            if key_u in DEFAULTS:
                current[key_u] = val
    current = _validate(current)
    lines = [
        "# Info Center per-machine platform — do not commit",
        "PANEL_LAYOUT=%s" % current["PANEL_LAYOUT"],
        "GPIO_PIN=%s" % current["GPIO_PIN"],
        "GLOBE_PUSH=%s" % current["GLOBE_PUSH"],
        "GLOBE_HOST=%s" % current["GLOBE_HOST"],
        "DIAG_BRIGHTNESS=%s" % current["DIAG_BRIGHTNESS"],
        "DISPLAY_NAME=%s" % current["DISPLAY_NAME"],
        "",
    ]
    tmp = PLATFORM_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    os.replace(tmp, PLATFORM_PATH)
    return current


def layout():
    return load_platform()[0]["PANEL_LAYOUT"]


def gpio_pin():
    return int(load_platform()[0]["GPIO_PIN"])


def globe_push_enabled():
    return load_platform()[0]["GLOBE_PUSH"] == "1"


def globe_host():
    return load_platform()[0]["GLOBE_HOST"]


def display_name():
    return load_platform()[0]["DISPLAY_NAME"]


#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("============================================================")
    print(" PLATFORM.py")
    print("============================================================")
    cfg, present = load_platform()
    print("path:    ", PLATFORM_PATH)
    print("present: ", present)
    for key in DEFAULTS:
        print("  %s=%s" % (key, cfg[key]))
    print("\nThis module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
