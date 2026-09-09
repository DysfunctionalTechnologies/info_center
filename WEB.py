#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  WEB.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import os
import threading
import logging
import secrets
import time
from   collections    import deque
from   flask          import Flask
from   flask          import render_template_string
from   flask          import jsonify
from   flask          import request
from   flask          import session
from   flask          import redirect

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import POWER_ON
from   CONFIG         import NETWORK_GOOD
from   CONFIG         import NETWORK_PROBLEM
from   CONFIG         import NETWORK_BAD
from   CONFIG         import NETWORK_UNTESTED
from   CONFIG         import ALERT_SOURCE_LIVE
from   CONFIG         import ALERT_SOURCE_WEB
from   CONFIG         import WEB_ALERT_HOLD
from   DIAGNOSTICS    import diagnostics
from   DATA_FETCHER   import fetch_weather
from   DATA_FETCHER   import fetch_earthquake
from   DATA_FETCHER   import fetch_exchange
from   DATA_FETCHER   import fetch_oil
from   DATA_FETCHER   import fetch_stocks
from   DATA_FETCHER   import fetch_holidays
from   DATA_FETCHER   import raise_alert
from   EEPROM         import save_persisted
from   PANEL          import power_on
from   PANEL          import power_off
from   PANEL          import mark_dirty
from   PLATFORM       import load_platform
from   PLATFORM       import save_platform
from   PLATFORM       import PLATFORM_PATH
from   WEB_login      import HTML_LOGIN
from   WEB_html       import HTML
from   WEB_diag       import HTML_DIAG
from   WEB_logs       import HTML_LOGS

logger = logging.getLogger(__name__)
app    = Flask(__name__)

app.secret_key         = secrets.token_hex(32)

def _load_web_auth():
    user = os.environ.get("INFOCENTER_WEB_USER", "").strip()
    pwd  = os.environ.get("INFOCENTER_WEB_PASS", "").strip()
    tuser = os.environ.get("INFOCENTER_TECH_USER", "").strip()
    tpwd  = os.environ.get("INFOCENTER_TECH_PASS", "").strip()
    path = os.environ.get(
        "INFOCENTER_WEB_AUTH_FILE",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".web_auth")
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f
                     if ln.strip() and not ln.startswith("#")]
        if len(lines) >= 2 and not (user and pwd):
            user, pwd = lines[0], lines[1]
        if len(lines) >= 4 and not (tuser and tpwd):
            tuser, tpwd = lines[2], lines[3]
    except OSError:
        pass
    if not (user and pwd):
        logger.warning("WEB auth missing – set .web_auth or INFOCENTER_WEB_USER/PASS")
    return user, pwd, tuser, tpwd

USERNAME, PASSWORD, TECH_USER, TECH_PASS = _load_web_auth()

active_session_id      = None
last_activity          = 0.0
SESSION_TIMEOUT        = 90.0
lock = threading.RLock()

last_force_refresh     = 0.0
FORCE_REFRESH_COOLDOWN = 60.0
_refreshing            = False
_refresh_lock          = threading.Lock()

LOG_RING_SIZE = 200
LOG_RING = deque(maxlen=LOG_RING_SIZE)
_log_ring_lock = threading.Lock()
_web_logs_enabled = False
_web_log_handler = None

_web_alert_lock = threading.Lock()
_web_alert_thunder     = False
_web_alert_heavy       = False
_web_alert_quake_y     = False
_web_alert_quake_r     = False
_WEB_ALERT_HOLD        = WEB_ALERT_HOLD

class RingLogHandler(logging.Handler):
    def emit(self, record):
        try:
            line = self.format(record)
        except Exception:
            line = record.getMessage()
        with _log_ring_lock:
            LOG_RING.append(line)

def attach_log_handler():
    global _web_log_handler, _web_logs_enabled
    root = logging.getLogger()
    if _web_log_handler is None:
        _web_log_handler = RingLogHandler()
        _web_log_handler.setLevel(logging.DEBUG)
        _web_log_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    if _web_log_handler not in root.handlers:
        root.addHandler(_web_log_handler)
    _web_logs_enabled = True
    logger.info("Web log capture ON")

def detach_log_handler():
    global _web_logs_enabled
    root = logging.getLogger()
    if _web_log_handler is not None and _web_log_handler in root.handlers:
        root.removeHandler(_web_log_handler)
    _web_logs_enabled = False
    logger.info("Web log capture OFF")

def apply_debug_mode(enabled):
    info_center.debug_mode = bool(enabled)
    logging.getLogger().setLevel(
        logging.DEBUG if info_center.debug_mode else logging.INFO
    )
    logger.info("Debug mode → %s", info_center.debug_mode)

def _apply_web_alerts():
    now = time.monotonic()
    with _web_alert_lock:
        thunder = _web_alert_thunder
        heavy   = _web_alert_heavy
        qy      = _web_alert_quake_y
        qr      = _web_alert_quake_r

    high = heavy or qr
    low  = thunder or qy
    testing = high or low

    with info_center.lock:
        info_center.web_alert_weather = bool(thunder or heavy)
        info_center.web_alert_quake   = bool(qy or qr)

        if testing:
            info_center.alert_source = "web_test"
        else:
            info_center.alert_source = "live"

        if high:
            info_center.alert_high_until = now + _WEB_ALERT_HOLD
        else:
            info_center.alert_high_until = 0.0
        if low:
            info_center.alert_low_until = now + _WEB_ALERT_HOLD
        else:
            info_center.alert_low_until = 0.0

        info_center.alert_until = max(info_center.alert_high_until,
                                      info_center.alert_low_until)
        if high:
            info_center.alert_level = 2
        elif low:
            info_center.alert_level = 1
        else:
            info_center.alert_level = 0

        if heavy:
            info_center.weather_code = 65
            info_center.weather_description = "HEAVY RAIN"
        elif thunder:
            info_center.weather_code = 95
            info_center.weather_description = "THUNDER"

        info_center.weather.last_built = 0.0

        if qr:
            info_center.quake_has_event = True
            info_center.quake_magnitude = 6.8
            info_center.quake_message = "M6.8 TEST QUAKE  15KM  0M AGO"
        elif qy:
            info_center.quake_has_event = True
            info_center.quake_magnitude = 5.5
            info_center.quake_message = "M5.5 TEST QUAKE  10KM  0M AGO"

        info_center.quake.last_built = 0.0

        items = []
        if thunder:
            items.append(("WX", "THUNDER", "Y"))
        if heavy:
            items.append(("WX", "HEAVY RAIN", "R"))
        if qy:
            items.append(("QK", "QUAKE 5+", "Y"))
        if qr:
            items.append(("QK", "QUAKE 6+", "R"))
        info_center.alert_items = items
        info_center.alert_nouns = [t for (_, t, _) in items]
        
def _clear_web_alerts():
    global _web_alert_thunder, _web_alert_heavy
    global _web_alert_quake_y, _web_alert_quake_r
    with _web_alert_lock:
        _web_alert_thunder = False
        _web_alert_heavy   = False
        _web_alert_quake_y = False
        _web_alert_quake_r = False
    with info_center.lock:
        info_center.web_alert_weather = False
        info_center.web_alert_quake   = False
        info_center.alert_source = "live"
        info_center.alert_level = 0
        info_center.alert_until = 0.0
        info_center.alert_high_until = 0.0
        info_center.alert_low_until = 0.0
        info_center.alert_items = []
        info_center.alert_nouns = []
        info_center.weather.last_built = 0.0
        info_center.quake.last_built = 0.0
        
def _clamp_bright(raw):
    val = int(raw)
    val = max(8, min(255, val))
    val = (val // 8) * 8
    return max(8, val)

def _mark_brightness_dirty():
    try:
        mark_dirty()
    except Exception:
        pass

def _apply_auto_target_if_needed():
    if not info_center.auto_brightness:
        return
    target = (info_center.day_brightness
              if info_center.day_time else info_center.night_brightness)
    if info_center.panel_brightness != target:
        info_center.panel_brightness = target
        _mark_brightness_dirty()

def check_timeout():
    global active_session_id, last_activity
    with lock:
        if active_session_id is not None:
            if (time.monotonic() - last_activity) > SESSION_TIMEOUT:
                active_session_id = None
                logger.info("Web session timed out – control released")

def is_authenticated():
    global active_session_id, last_activity
    check_timeout()
    sid = session.get("sid")
    with lock:
        if sid is None or sid != active_session_id:
            return False
        last_activity = time.monotonic()
        return True

def is_tech():
    if not is_authenticated():
        return False
    return session.get("role") == "tech"

def _deny_json():
    return jsonify({"error": "unauthorized"}), 401

def force_pattern(pattern_num):
    if pattern_num < 1:
        return
    with info_center.lock:
        info_center.current_pattern = pattern_num
        info_center.pattern_init = False
        info_center.pattern_end_time = time.monotonic() + 0.05
        sc = info_center.scroll
        sc.phase = 0
        sc.text = ""
        sc.pos = 0
        sc.buffer = None
        sc.hold_until = 0.0
        sc.next = 0.0
        ex = info_center.exchange
        ex.dissolve_phase = 0
        ex.dissolve_pixels = []
        ex.dissolve_next = 0.0
        ex.hold_start = 0.0
    logger.info("Forced pattern → %s", pattern_num)

def _force_refresh_worker():
    global _refreshing
    try:
        logger.info("Force refresh started")
        fetch_weather()
        fetch_earthquake()
        fetch_exchange()
        fetch_oil()
        fetch_stocks()
        fetch_holidays()
        logger.info("Force refresh completed")
    except Exception:
        logger.exception("Force refresh failed")
    finally:
        with _refresh_lock:
            _refreshing = False

def do_force_refresh():
    global last_force_refresh, _refreshing
    now = time.monotonic()
    with _refresh_lock:
        if _refreshing:
            return False
        if (now - last_force_refresh) < FORCE_REFRESH_COOLDOWN:
            return False
        last_force_refresh = now
        _refreshing = True
    threading.Thread(
        target=_force_refresh_worker,
        name="ForceRefresh",
        daemon=True
    ).start()
    return True

def _platform_fields_from_request():
    return {
        "PANEL_LAYOUT": request.form.get("PANEL_LAYOUT", "16x16"),
        "GPIO_PIN": request.form.get("GPIO_PIN", "21"),
        "GLOBE_PUSH": "1" if request.form.get("GLOBE_PUSH") else "0",
        "GLOBE_HOST": request.form.get("GLOBE_HOST", "192.168.0.223"),
        "DIAG_BRIGHTNESS": request.form.get("DIAG_BRIGHTNESS", ""),
        "DISPLAY_NAME": request.form.get("DISPLAY_NAME", ""),
    }

def _apply_platform_cfg(cfg):
    info_center.panel_layout = cfg["PANEL_LAYOUT"]
    try:
        info_center.strip_gpio = int(cfg["GPIO_PIN"])
    except (TypeError, ValueError):
        pass
    enabled = cfg["GLOBE_PUSH"] == "1"
    info_center.globe_push_enabled = enabled
    save_persisted()
    from GLOBE_LINK import push_globe
    if enabled:
        push_globe(force=True)
    else:
        push_globe(force=True, mode="OFF")
    logger.info("Platform saved %s gpio=%s globe=%s host=%s",
                cfg["PANEL_LAYOUT"], cfg["GPIO_PIN"],
                cfg["GLOBE_PUSH"], cfg.get("GLOBE_HOST", ""))

@app.route("/login", methods=["GET", "POST"])
def login():
    global active_session_id, last_activity
    if request.method == "POST":
        if not USERNAME or not PASSWORD:
            return render_template_string(
                HTML_LOGIN,
                error="Web login is not configured on this device."
            )
        user = request.form.get("username", "")
        pwd  = request.form.get("password", "")

        role = None
        if TECH_USER and TECH_PASS and user == TECH_USER and pwd == TECH_PASS:
            role = "tech"
        elif user == USERNAME and pwd == PASSWORD:
            role = "user"

        if role is None:
            return render_template_string(
                HTML_LOGIN,
                error="Invalid username or password"
            )

        with lock:
            check_timeout()
            if active_session_id is not None:
                return render_template_string(
                    HTML_LOGIN,
                    error="Display is currently in use by another user.<br>Try again later."
                )
            sid = secrets.token_hex(16)
            session.clear()
            session["sid"] = sid
            session["role"] = role
            active_session_id = sid
            last_activity = time.monotonic()
            logger.info("Web user logged in and took control role=%s", role)
            return redirect("/")
    if is_authenticated():
        return redirect("/")
    return render_template_string(HTML_LOGIN, error=None)

@app.route("/logout")
def logout():
    global active_session_id
    with lock:
        if session.get("sid") == active_session_id:
            active_session_id = None
            logger.info("Web user logged out – control released")
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    if not is_authenticated():
        return redirect("/login")
    return render_template_string(HTML, role=session.get("role"))

@app.route("/diag")
def diag():
    if not is_authenticated():
        return redirect("/login")
    if not is_tech():
        return redirect("/")
    plat, plat_present = load_platform()
    return render_template_string(
        HTML_DIAG,
        plat=plat,
        plat_present=plat_present,
        plat_path=PLATFORM_PATH,
    )

@app.route("/logs")
def logs_page():
    if not is_authenticated():
        return redirect("/login")
    if not is_tech():
        return redirect("/")
    return render_template_string(HTML_LOGS)

@app.route("/logs.json")
def logs_json():
    if not is_tech():
        return _deny_json()
    with _log_ring_lock:
        lines = list(LOG_RING)
    return jsonify({
        "lines": lines,
        "count": len(lines),
        "web_logs": bool(_web_logs_enabled),
        "debug_mode": bool(info_center.debug_mode),
    })
    
@app.route("/status")
def status():
    if not is_authenticated():
        return _deny_json()
    now = time.monotonic()
    with _refresh_lock:
        refreshing = _refreshing
    remaining = max(0, int(FORCE_REFRESH_COOLDOWN - (now - last_force_refresh)))

    inet = info_center.internet_status
    if inet == NETWORK_GOOD:
        inet_str, inet_color = "GOOD", "#0f0"
    elif inet == NETWORK_PROBLEM:
        inet_str, inet_color = "PARTIAL", "#ff0"
    elif inet == NETWORK_BAD:
        inet_str, inet_color = "BAD", "#f00"
    else:
        inet_str, inet_color = "UNTESTED", "#48f"

    high = now < getattr(info_center, "alert_high_until", 0.0)
    low  = now < getattr(info_center, "alert_low_until", 0.0)
    if high and low:
        globe_str, globe_color = "ALERT HIGH+LOW (R/Y/K)", "#f80"
    elif high or (info_center.alert_level == 2 and now < info_center.alert_until):
        globe_str, globe_color = "ALERT HIGH (flashing)", "#f00"
    elif low or (info_center.alert_level == 1 and now < info_center.alert_until):
        globe_str, globe_color = "ALERT LOW (flashing)", "#ff0"
    else:
        globe_str, globe_color = inet_str, inet_color

    with _web_alert_lock:
        a_thunder = _web_alert_thunder
        a_heavy   = _web_alert_heavy
        a_qy      = _web_alert_quake_y
        a_qr      = _web_alert_quake_r

    symbols = list(getattr(info_center, "stock_symbols", ["", "", "", "", ""]))
    while len(symbols) < 5:
        symbols.append("")
    valid = list(getattr(info_center, "stock_valid", [False] * 5))
    while len(valid) < 5:
        valid.append(False)

    return jsonify({
        "brightness": info_center.panel_brightness,
        "auto_brightness": bool(info_center.auto_brightness),
        "military_time": bool(info_center.military_time),
        "temp_celsius": bool(getattr(info_center, "temp_celsius", True)),
        "day_brightness": int(getattr(info_center, "day_brightness", 63)),
        "night_brightness": int(getattr(info_center, "night_brightness", 31)),
        "debug_mode": bool(info_center.debug_mode),
        "web_logs": _web_logs_enabled,
        "power_level": info_center.power_level,
        "power": info_center.power_flag,
        "refresh_cooldown": remaining,
        "refreshing": refreshing,
        "internet": inet_str,
        "internet_color": inet_color,
        "globe": globe_str,
        "globe_color": globe_color,
        "globe_push": bool(getattr(info_center, "globe_push_enabled", False)),
        "alert_thunder": a_thunder,
        "alert_heavy": a_heavy,
        "alert_quake_yellow": a_qy,
        "alert_quake_red": a_qr,
        "role": session.get("role"),
        "exchange_primary":   getattr(info_center, "exchange_primary",
                              getattr(info_center, "exchange_base", "USD")),
        "exchange_secondary": getattr(info_center, "exchange_secondary",
                              getattr(info_center, "exchange_quote", "PHP")),
        "exchange_base":      getattr(info_center, "exchange_primary",
                              getattr(info_center, "exchange_base", "USD")),
        "exchange_quote":     getattr(info_center, "exchange_secondary",
                              getattr(info_center, "exchange_quote", "PHP")),
        "pair_rate":          float(getattr(info_center, "pair_rate", 0.0) or 0.0),
        "usd_to_primary":     float(getattr(info_center, "usd_to_primary", 0.0) or 0.0),
        "primary_valid":      bool(getattr(info_center,  "primary_valid", True)),
        "secondary_valid":    bool(getattr(info_center,  "secondary_valid", True)),
        "show_pacman":        bool(getattr(info_center,  "show_pacman", True)),
        "show_weather":       bool(getattr(info_center,  "show_weather", True)),
        "show_exchange":      bool(getattr(info_center,  "show_exchange", True)),
        "show_oil":           bool(getattr(info_center,  "show_oil", True)),
        "show_stocks":        bool(getattr(info_center,  "show_stocks", True)),
        "show_earthquake":    bool(getattr(info_center,  "show_earthquake", True)),
        "stock_symbols":      symbols[:5],
        "stock_valid":        valid[:5],
    })

@app.route("/set_globe_push", methods=["POST"])
def route_set_globe_push():
    if not is_authenticated():
        return _deny_json()
    raw = str(request.args.get("value", "0")).lower()
    enabled = raw in ("1", "true", "yes", "on")
    info_center.globe_push_enabled = enabled
    try:
        save_platform({"GLOBE_PUSH": "1" if enabled else "0"})
    except Exception:
        logger.warning("platform GLOBE_PUSH save failed", exc_info=True)
    from GLOBE_LINK import push_globe
    if enabled:
        push_globe(force=True)
    else:
        push_globe(force=True, mode="OFF")
    save_persisted()
    logger.info("Globe push → %s", enabled)
    return status()

@app.route("/set_exchange_pair", methods=["POST"])
def route_set_exchange_pair():
    if not is_authenticated():
        return _deny_json()
    cur_p = getattr(info_center, "exchange_primary",
                    getattr(info_center, "exchange_base", "USD"))
    cur_s = getattr(info_center, "exchange_secondary",
                    getattr(info_center, "exchange_quote", "PHP"))
    raw_p = request.args.get("primary", request.args.get("base"))
    raw_s = request.args.get("secondary", request.args.get("quote"))
    if raw_p is None:
        primary = cur_p
    else:
        primary = "".join(ch for ch in str(raw_p).upper() if "A" <= ch <= "Z")[:3] or cur_p
    if raw_s is None:
        secondary = cur_s
    else:
        secondary = "".join(ch for ch in str(raw_s).upper() if "A" <= ch <= "Z")[:3] or cur_s
    with info_center.lock:
        info_center.exchange_primary   = primary
        info_center.exchange_secondary = secondary
        info_center.exchange_base      = primary
        info_center.exchange_quote     = secondary
        info_center.usd_to_primary     = 0.0
        info_center.usd_to_secondary   = 0.0
        info_center.pair_rate          = 0.0
        info_center.exchange_rate      = 0.0
        info_center.last_exchange_rate = 0.0
        info_center.primary_valid      = True
        info_center.secondary_valid    = True
        info_center.exchange.last_built = 0.0
        info_center.oil.last_built      = 0.0
        if hasattr(info_center, "stocks"):
            info_center.stocks.last_built = 0.0
    save_persisted()
    logger.info("FX pair → %s / %s (EEPROM V3)", primary, secondary)
    threading.Thread(target=fetch_exchange, name="FXPairFetch", daemon=True).start()
    return status()

_PATTERN_ENABLE_KEYS = {
    "pacman":     "show_pacman",
    "weather":    "show_weather",
    "exchange":   "show_exchange",
    "oil":        "show_oil",
    "stocks":     "show_stocks",
    "earthquake": "show_earthquake",
}

@app.route("/set_pattern_enable", methods=["POST"])
def route_set_pattern_enable():
    if not is_authenticated():
        return _deny_json()
    name = str(request.args.get("name", "")).strip().lower()
    attr = _PATTERN_ENABLE_KEYS.get(name)
    if not attr:
        return status()
    raw = str(request.args.get("value", "1")).lower()
    enabled = raw in ("1", "true", "yes", "on")
    setattr(info_center, attr, enabled)
    save_persisted()
    logger.info("Pattern %s → %s (EEPROM V3)", attr, enabled)
    return status()

@app.route("/set_stock_symbols", methods=["POST"])
def route_set_stock_symbols():
    if not is_authenticated():
        return _deny_json()
    raw = request.args.get("symbols", "")
    parts = [p.strip().upper() for p in raw.replace(",", " ").split()]
    out = []
    for p in parts:
        s = "".join(ch for ch in p if ch.isalnum() or ch in ".-")[:8]
        if s and s not in out:
            out.append(s)
        if len(out) == 5:
            break
    while len(out) < 5:
        out.append("")
    with info_center.lock:
        info_center.stock_symbols = out
        info_center.stock_valid = [False] * 5
        if hasattr(info_center, "stocks"):
            info_center.stocks.last_built = 0.0
    save_persisted()
    logger.info("Stocks → %s (EEPROM V3)", out)
    threading.Thread(target=fetch_stocks, name="StockFetch", daemon=True).start()
    return status()

@app.route("/set_debug", methods=["POST"])
def route_set_debug():
    if not is_tech():
        return _deny_json()
    raw = str(request.args.get("value", "1")).lower()
    apply_debug_mode(raw in ("1", "true", "yes", "on"))
    return status()

@app.route("/set_web_logs", methods=["POST"])
def route_set_web_logs():
    if not is_tech():
        return _deny_json()
    raw = str(request.args.get("value", "0")).lower()
    if raw in ("1", "true", "yes", "on"):
        attach_log_handler()
    else:
        detach_log_handler()
    return status()

@app.route("/set_brightness", methods=["POST"])
def route_set_brightness():
    if not is_authenticated():
        return _deny_json()
    try:
        val = _clamp_bright(request.args.get("value", info_center.panel_brightness))
    except (TypeError, ValueError):
        return status()
    info_center.panel_brightness = val
    info_center.auto_brightness = False
    _mark_brightness_dirty()
    save_persisted()
    return status()

@app.route("/set_day_brightness", methods=["POST"])
def route_set_day_brightness():
    if not is_authenticated():
        return _deny_json()
    try:
        val = _clamp_bright(request.args.get("value", info_center.day_brightness))
    except (TypeError, ValueError):
        return status()
    info_center.day_brightness = val
    _apply_auto_target_if_needed()
    save_persisted()
    return status()

@app.route("/set_night_brightness", methods=["POST"])
def route_set_night_brightness():
    if not is_authenticated():
        return _deny_json()
    try:
        val = _clamp_bright(request.args.get("value", info_center.night_brightness))
    except (TypeError, ValueError):
        return status()
    info_center.night_brightness = val
    _apply_auto_target_if_needed()
    save_persisted()
    return status()

@app.route("/set_auto_brightness", methods=["POST"])
def route_set_auto_brightness():
    if not is_authenticated():
        return _deny_json()
    raw = str(request.args.get("value", "1")).lower()
    info_center.auto_brightness = raw in ("1", "true", "yes", "on")
    _apply_auto_target_if_needed()
    save_persisted()
    return status()

@app.route("/set_military_time", methods=["POST"])
def route_set_military_time():
    if not is_authenticated():
        return _deny_json()
    raw = str(request.args.get("value", "1")).lower()
    info_center.military_time = raw in ("1", "true", "yes", "on")
    save_persisted()
    return status()

@app.route("/set_temp_celsius", methods=["POST"])
def route_set_temp_celsius():
    if not is_authenticated():
        return _deny_json()
    raw = str(request.args.get("value", "1")).lower()
    info_center.temp_celsius = raw in ("1", "true", "yes", "on")
    save_persisted()
    return status()

@app.route("/power_on", methods=["POST"])
def route_power_on():
    if not is_authenticated():
        return _deny_json()
    info_center.power_level = POWER_ON
    info_center.power_flag = True
    power_on()
    return status()

@app.route("/power_off", methods=["POST"])
def route_power_off():
    if not is_authenticated():
        return _deny_json()
    power_off()
    return status()

@app.route("/force/<int:pattern_num>", methods=["POST"])
def route_force(pattern_num):
    if not is_tech():
        return _deny_json()
    force_pattern(pattern_num)
    return status()

@app.route("/force_refresh", methods=["POST"])
def route_force_refresh():
    if not is_tech():
        return _deny_json()
    do_force_refresh()
    return status()

@app.route("/diag_test/<int:test_num>", methods=["POST"])
def route_diag_test(test_num):
    if not is_tech():
        return _deny_json()
    if test_num not in diagnostics:
        return status()
    if getattr(info_center, "diag_busy", False):
        logger.info("Diagnostic already running – ignored")
        return status()

    def _run():
        info_center.diag_busy = True
        time.sleep(0.08)
        logger.info("Web diagnostic %s started", test_num)
        try:
            diagnostics[test_num]()
        except Exception as e:
            logger.warning("Web diagnostic %s failed: %s", test_num, e)
        finally:
            info_center.diag_busy = False
            info_center.pattern_init = False
            info_center.pattern_end_time = time.monotonic()
            logger.info("Web diagnostic %s finished", test_num)

    threading.Thread(target=_run, name="WebDiag", daemon=True).start()
    return status()

@app.route("/alert/reset", methods=["POST"])
def route_alert_reset():
    if not is_tech():
        return _deny_json()
    _clear_web_alerts()
    logger.info("Alerts reset via web")
    try:
        fetch_weather()
    except Exception:
        pass
    return status()

@app.route("/alert/thunder", methods=["POST"])
def route_alert_thunder():
    global _web_alert_thunder
    if not is_tech():
        return _deny_json()
    with _web_alert_lock:
        _web_alert_thunder = not _web_alert_thunder
        on = _web_alert_thunder
    _apply_web_alerts()
    logger.info("Web thunder toggle → %s", on)
    return status()

@app.route("/alert/heavy", methods=["POST"])
def route_alert_heavy():
    global _web_alert_heavy
    if not is_tech():
        return _deny_json()
    with _web_alert_lock:
        _web_alert_heavy = not _web_alert_heavy
        on = _web_alert_heavy
    _apply_web_alerts()
    logger.info("Web heavy rain toggle → %s", on)
    return status()

@app.route("/alert/quake_yellow", methods=["POST"])
def route_alert_quake_y():
    global _web_alert_quake_y
    if not is_tech():
        return _deny_json()
    with _web_alert_lock:
        _web_alert_quake_y = not _web_alert_quake_y
        on = _web_alert_quake_y
    _apply_web_alerts()
    logger.info("Web quake yellow toggle → %s", on)
    return status()

@app.route("/alert/quake_red", methods=["POST"])
def route_alert_quake_r():
    global _web_alert_quake_r
    if not is_tech():
        return _deny_json()
    with _web_alert_lock:
        _web_alert_quake_r = not _web_alert_quake_r
        on = _web_alert_quake_r
    _apply_web_alerts()
    logger.info("Web quake red toggle → %s", on)
    return status()

@app.route("/platform_save", methods=["POST"])
def route_platform_save():
    if not is_tech():
        return redirect("/")
    cfg = save_platform(_platform_fields_from_request())
    _apply_platform_cfg(cfg)
    return redirect("/diag")

@app.route("/platform_save_reboot", methods=["POST"])
def route_platform_save_reboot():
    if not is_tech():
        return redirect("/")
    if request.form.get("confirm") != "REBOOT":
        return redirect("/diag")
    cfg = save_platform(_platform_fields_from_request())
    _apply_platform_cfg(cfg)
    logger.info("Platform saved – rebooting")
    threading.Thread(
        target=lambda: (time.sleep(0.4), os.system("sudo /sbin/reboot")),
        name="PlatformReboot",
        daemon=True
    ).start()
    return "Rebooting...", 200

_web_started = False

def start_web():
    global _web_started
    if _web_started:
        logger.info("Web control already running – skipping")
        return
    _web_started = True
    apply_debug_mode(info_center.debug_mode)
    host = "0.0.0.0"

    def run():
        app.run(host=host, port=5000, debug=False, use_reloader=False)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    logger.info("Web control started on http://%s:5000", host)

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
