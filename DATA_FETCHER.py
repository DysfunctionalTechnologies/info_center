#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 5, 2026
# Module:  DATA_FETCHER.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import json
import logging
import threading
import time
import urllib.request
from   datetime     import datetime, timezone, date, timedelta

# Project Imports
from   CONFIG       import info_center
from   CONFIG       import POWER_SLEEP
from   CONFIG       import WEATHER_HEAVY_CODES
from   CONFIG       import WEATHER_THUNDER_CODES
from   CONFIG       import QUAKE_ALERT_MAJOR
from   CONFIG       import QUAKE_ALERT_MINOR
from   CONFIG       import EXCHANGE_ALERT_MAJOR
from   CONFIG       import EXCHANGE_ALERT_MINOR
from   CONFIG       import EXCHANGE_ALERT_MAJOR_PCT
from   CONFIG       import EXCHANGE_ALERT_MINOR_PCT
from   EEPROM       import eeprom
from   EEPROM       import save_persisted
from   TEMPERATURE  import read_temp

logger = logging.getLogger(__name__)

_FETCH_HEADERS = {
    "User-Agent": (
        f"InfoCenter/{info_center.version_string.lstrip('Vv')} "
        "(Raspberry Pi LED display)"
    )
}

_FETCH_BACKOFF = (20.0, 60.0, 180.0)
_oil_asof      = ""          # local YYYY-MM-DD of the live tick

class _FetchRetry:
    def __init__(self, name):
        self.name = name
        self.level = 0
        self.next_try = 0.0

    def allow(self, now):
        return now >= self.next_try

    def success(self):
        self.level = 0
        self.next_try = 0.0

    def failure(self):
        delay = _FETCH_BACKOFF[min(self.level, len(_FETCH_BACKOFF) - 1)]
        if self.level < len(_FETCH_BACKOFF) - 1:
            self.level += 1
        self.next_try = time.monotonic() + delay
        logger.warning("%s fetch failed – retry in %.0fs", self.name, delay)

def is_data_fresh(last_update, max_age):
    if last_update <= 0.0:
        return False
    return (time.monotonic() - last_update) <= max_age

def raise_alert(level, source=""):
    now = time.monotonic()
    with info_center.lock:
        if getattr(info_center, "alert_source", "live") == "web_test":
            logger.info("Live alert %s from %s ignored (web test active)",
                        level, source or "?")
            return
        if level >= 2:
            info_center.alert_high_until = now + info_center.alert_duration
        elif level == 1:
            info_center.alert_low_until = now + info_center.alert_duration
        else:
            return
        info_center.alert_until = max(info_center.alert_high_until,
                                      info_center.alert_low_until)
        info_center.alert_level = 2 if now < info_center.alert_high_until else 1
        info_center.alert_source = "live"

        src = (source or "").lower()
        item = None
        if "heavy" in src:
            item = ("WX", "HEAVY RAIN", "R")
        elif "thunder" in src:
            item = ("WX", "THUNDER", "Y")
        elif "quake-major" in src or ("quake" in src and level >= 2):
            item = ("QK", "QUAKE 6+", "R")
        elif "quake" in src:
            item = ("QK", "QUAKE 5+", "Y")
        elif "fx-major" in src or ("fx" in src and level >= 2):
            item = ("FX", "FX", "R")
        elif "fx" in src:
            item = ("FX", "FX", "Y")

        items = list(getattr(info_center, "alert_items", []) or [])
        if item and item not in items:
            items.append(item)
        info_center.alert_items = items
        info_center.alert_nouns = [t for (_, t, _) in items]
    logger.info("Alert %s from %s", level, source or "?")
        
def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={info_center.weather_lat}"
        f"&longitude={info_center.weather_lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,"
        "wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day"
        "&temperature_unit=celsius&wind_speed_unit=kmh&timezone=auto"
    )

    data = _safe_get(url)
    if not data:
        return False

    try:
        current = data["current"]
        temp_c = float(current["temperature_2m"])
        with info_center.lock:
            info_center.weather_temp_c       = temp_c
            info_center.weather_temp_f       = temp_c * 9.0 / 5.0 + 32.0
            info_center.weather_humidity     = int(current["relative_humidity_2m"])
            info_center.weather_wind_kmh     = float(current["wind_speed_10m"])
            info_center.weather_wind_dir     = float(current["wind_direction_10m"])
            info_center.weather_wind_gusts   = float(current.get("wind_gusts_10m", 0.0))
            info_center.weather_is_day       = int(current.get("is_day", 1))
            info_center.weather_last_update  = time.monotonic()
            if not getattr(info_center, "web_alert_weather", False):
                info_center.weather_code = int(current["weather_code"])
            code = info_center.weather_code

        if not getattr(info_center, "web_alert_weather", False):
            if code in WEATHER_HEAVY_CODES:
                raise_alert(2, f"weather-heavy code={code}")
            elif code in WEATHER_THUNDER_CODES:
                raise_alert(1, f"weather-thunder code={code}")

        return True
    except Exception as e:
        logger.warning("Weather parse error: %s", e)
        return False

def fetch_earthquake():
    try:
        start_ts = datetime.now(timezone.utc).timestamp() - (7 * 24 * 3600)
        start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            f"?format=geojson"
            f"&latitude={info_center.quake_lat}"
            f"&longitude={info_center.quake_lon}"
            f"&maxradiuskm={info_center.quake_radius_km}"
            f"&minmagnitude={info_center.quake_min_magnitude}"
            f"&orderby=time"
            f"&limit=5"
            f"&starttime={start_str}"
        )

        data = _safe_get(url, timeout=10)
        if not data:
            return False

        features = data.get("features", [])

        with info_center.lock:
            info_center.quake_last_update = time.monotonic()
            if getattr(info_center, "web_alert_quake", False):
                return True

            if not features:
                info_center.quake_has_event = False
                info_center.quake_magnitude = 0.0
                info_center.quake_message = "NO RECENT QUAKES"
                return True

            props = features[0]["properties"]
            coords = features[0]["geometry"].get("coordinates", [0.0, 0.0, 0.0])

            mag   = float(props.get("mag", 0.0))
            place = str(props.get("place", "UNKNOWN")).upper()
            depth = float(coords[2]) if len(coords) > 2 else 0.0
            t_ms  = int(props.get("time", 0))

            age_sec = (datetime.now(timezone.utc).timestamp() * 1000 - t_ms) / 1000.0
            if age_sec < 3600:
                age_str = f"{int(age_sec // 60)}M AGO"
            elif age_sec < 86400:
                age_str = f"{int(age_sec // 3600)}H AGO"
            else:
                age_str = f"{int(age_sec // 86400)}D AGO"

            info_center.quake_has_event = True
            info_center.quake_magnitude = mag
            info_center.quake_message   = f"M{mag:.1f} {place}  {depth:.0f}KM  {age_str}"

        if info_center.debug_mode:
            logger.debug("QUAKE: mag=%.1f  place=%s", mag, place)

        if mag >= QUAKE_ALERT_MAJOR:
            raise_alert(2, f"quake-major mag={mag:.1f}")
        elif mag >= QUAKE_ALERT_MINOR:
            raise_alert(1, f"quake-minor mag={mag:.1f}")

        return True

    except Exception as e:
        logger.warning("Earthquake fetch error: %s", e)
        return False

def _norm_ccy(raw, fallback):
    s = "".join(ch for ch in str(raw).upper() if "A" <= ch <= "Z")
    return s[:3] if len(s) == 3 else fallback

def _usd_rate(rates, code):
    if code == "USD":
        return 1.0, True
    try:
        val = float(rates[code])
        return val, val > 0.0
    except (KeyError, TypeError, ValueError):
        return 0.0, False

def fetch_exchange():
    primary   = _norm_ccy(getattr(info_center, "exchange_primary",
                 getattr(info_center, "exchange_base", "USD")), "USD")
    secondary = _norm_ccy(getattr(info_center, "exchange_secondary",
                 getattr(info_center, "exchange_quote", "PHP")), "PHP")

    data = _safe_get("https://open.er-api.com/v6/latest/USD")
    if not data:
        return False

    try:
        rates = data.get("rates") or {}
        usd_p, ok_p = _usd_rate(rates, primary)
        usd_s, ok_s = _usd_rate(rates, secondary)
        pair = (usd_s / usd_p) if (ok_p and ok_s and usd_p > 0.0) else 0.0

        primary = getattr(info_center, "exchange_primary",
                          getattr(info_center, "exchange_base", "USD"))
        secondary = getattr(info_center, "exchange_secondary",
                            getattr(info_center, "exchange_quote", "PHP"))

        with info_center.lock:
            old_pair = getattr(info_center, "pair_rate", 0.0) or info_center.exchange_rate
            had_prior = (old_pair > 0.0 and info_center.exchange_last_update > 0.0)
            baseline = old_pair if had_prior else info_center.last_exchange_rate

            if had_prior:
                info_center.last_exchange_rate = old_pair
            elif info_center.last_exchange_rate <= 0.0 and pair > 0.0:
                info_center.last_exchange_rate = pair
                baseline = 0.0

            info_center.exchange_primary   = primary
            info_center.exchange_secondary = secondary
            info_center.exchange_base      = primary
            info_center.exchange_quote     = secondary
            info_center.usd_to_primary     = usd_p
            info_center.usd_to_secondary   = usd_s
            info_center.pair_rate          = pair
            info_center.primary_valid      = ok_p
            info_center.secondary_valid    = ok_s
            info_center.exchange_rate      = pair
            info_center.exchange_last_update = time.monotonic()
            info_center.exchange.last_built = 0.0
            info_center.oil.last_built = 0.0

        if baseline > 0.0 and pair > 0.0:
            delta_pct = abs(pair - baseline) / baseline
            if delta_pct >= EXCHANGE_ALERT_MAJOR_PCT:
                raise_alert(2, "fx-major %s/%s pct=%.4f" %
                            (primary, secondary, delta_pct))
            elif delta_pct >= EXCHANGE_ALERT_MINOR_PCT:
                raise_alert(1, "fx-minor %s/%s pct=%.4f" %
                            (primary, secondary, delta_pct))

        if not ok_p:
            logger.warning("FX primary code invalid: %s", primary)
        if not ok_s:
            logger.warning("FX secondary code invalid: %s", secondary)

        save_persisted()
        return True
        
    except Exception as e:
        logger.warning("Exchange parse error: %s", e)
        return False
                
def fetch_oil():
    global _oil_asof

    data = _safe_get("https://api.oilpriceapi.com/v1/demo/prices")
    if not data:
        return False

    try:
        prices = {p["code"]: float(p["price"]) for p in data["data"]["prices"]}

        new_wti   = prices.get("WTI_USD", 0.0)
        new_brent = prices.get("BRENT_CRUDE_USD", 0.0)
        new_urals = prices.get("URALS_CRUDE_USD", 0.0)

        if new_wti <= 0.0 and new_brent <= 0.0 and new_urals <= 0.0:
            logger.warning("Oil fetch ignored – demo/zero prices")
            return False

        today = time.strftime("%Y-%m-%d")

        with info_center.lock:
            had_live = (info_center.oil_last_update > 0.0 and
                        (info_center.oil_wti > 0.0 or
                         info_center.oil_brent > 0.0 or
                         info_center.oil_urals > 0.0))

            if had_live and _oil_asof and _oil_asof != today:
                if info_center.oil_wti > 0.0:
                    info_center.prev_wti = info_center.oil_wti
                if info_center.oil_brent > 0.0:
                    info_center.prev_brent = info_center.oil_brent
                if info_center.oil_urals > 0.0:
                    info_center.prev_urals = info_center.oil_urals
                rolled = True
            else:
                rolled = False

            if new_wti > 0.0:
                info_center.oil_wti = new_wti
            if new_brent > 0.0:
                info_center.oil_brent = new_brent
            if new_urals > 0.0:
                info_center.oil_urals = new_urals

            info_center.oil_last_update = time.monotonic()

        if rolled:
            save_persisted()
            logger.info("Oil previous close rolled %s → %s", _oil_asof, today)

        _oil_asof = today
        return True

    except Exception as e:
        logger.warning("Oil parse error: %s", e)
        return False

def _norm_symbol(raw):
    s = "".join(ch for ch in str(raw).upper() if ch.isalnum() or ch in ".-")
    return s[:8]

def _fetch_one_stock(sym):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1d&interval=1d" % sym
    data = _safe_get(url, timeout=10)
    if not data:
        return 0.0, 0.0, False
    try:
        meta = data["chart"]["result"][0]["meta"]
        price = float(meta.get("regularMarketPrice") or 0.0)
        prev  = float(meta.get("chartPreviousClose") or
                      meta.get("previousClose") or 0.0)
        return price, prev, price > 0.0
    except (KeyError, TypeError, ValueError, IndexError):
        return 0.0, 0.0, False

def fetch_stocks():
    symbols = list(getattr(info_center, "stock_symbols", ["", "", "", "", ""]))
    while len(symbols) < 5:
        symbols.append("")
    symbols = [_norm_symbol(s) for s in symbols[:5]]

    if not any(symbols):
        with info_center.lock:
            info_center.stock_prices = [0.0] * 5
            info_center.stock_prevs  = [0.0] * 5
            info_center.stock_valid  = [False] * 5
            info_center.stock_last_update = time.monotonic()
            info_center.stocks.last_built = 0.0
        return True

    prices, prevs, flags = [], [], []
    any_ok = False
    for sym in symbols:
        if not sym:
            prices.append(0.0); prevs.append(0.0); flags.append(False)
            continue
        price, prev, ok = _fetch_one_stock(sym)
        prices.append(price)
        prevs.append(prev)
        flags.append(ok)
        any_ok = any_ok or ok
        if not ok:
            logger.warning("Stock %s missing or invalid", sym)

    with info_center.lock:
        info_center.stock_symbols = symbols
        info_center.stock_prices  = prices
        info_center.stock_prevs   = prevs
        info_center.stock_valid   = flags
        info_center.stock_last_update = time.monotonic()
        info_center.stocks.last_built = 0.0

    return True if any_ok or not any(symbols) else False

def _easter(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)

def _nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    d += timedelta(weeks=n - 1)
    return d

def _last_monday(year, month):
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    d -= timedelta(days=(d.weekday() - 0) % 7)
    return d

def _us_election_day(year):
    d = date(year, 11, 1)
    d += timedelta(days=(0 - d.weekday()) % 7)
    return d + timedelta(days=1)

def _extra_holidays(year):
    easter = _easter(year)
    return {
        date(year, 2, 14): "VALENTINES DAY",
        date(year, 3, 17): "ST PATRICKS DAY",
        easter - timedelta(days=46): "ASH WEDNESDAY",
        easter - timedelta(days=7): "PALM SUNDAY",
        easter - timedelta(days=2): "GOOD FRIDAY",
        easter: "EASTER",
        _nth_weekday(year, 5, 6, 2): "MOTHERS DAY",
        _last_monday(year, 5): "MEMORIAL DAY",
        date(year, 6, 14): "FLAG DAY",
        _nth_weekday(year, 6, 6, 3): "FATHERS DAY",
        _nth_weekday(year, 9, 0, 1): "LABOR DAY",
        date(year, 9, 11): "PATRIOT DAY",
        date(year, 10, 31): "HALLOWEEN",
        _us_election_day(year): "ELECTION DAY",
        date(year, 12, 24): "CHRISTMAS EVE",
        date(year, 12, 31): "NEW YEARS EVE",
    }

def _norm_holiday(name):
    s = str(name or "").replace("'", "").replace("’", "").strip().upper()
    s = s.replace("LABOUR", "LABOR")
    if s in ("", "HOLIDAY", "US HOLIDAY", "PH HOLIDAY"):
        return ""
    if s.startswith("US "):
        s = s[3:]
    if s.startswith("PH "):
        s = s[3:]
    return s

def collect(cc):
    out = []
    data = _safe_get(
        f"https://nagerholidays.com/api/v4/Holidays/{cc}/{year}",
        timeout=10
    )
    if not isinstance(data, list):
        return out
    for h in data:
        if str(h.get("date", ""))[:10] != today:
            continue
        raw = h.get("name") or h.get("localName") or ""
        name = _norm_holiday(raw)
        if name and name not in out:
            out.append(name)
    return out
    
def fetch_holidays():
    try:
        today = time.strftime("%Y-%m-%d")
        year  = time.strftime("%Y")

        def collect(cc):
            out = []
            data = _safe_get(
                f"https://nagerholidays.com/api/v4/Holidays/{cc}/{year}",
                timeout=10
            )
            if not isinstance(data, list):
                return out
            for h in data:
                if str(h.get("date", ""))[:10] != today:
                    continue
                # US official spelling lives in localName; name is often British
                raw = h.get("localName") if cc == "US" else (h.get("name") or h.get("localName"))
                name = _norm_holiday(raw)
                if name and name not in out:
                    out.append(name)
            return out

        ph_names = collect("PH")
        us_names = collect("US")

        if ph_names and us_names:
            names = list(ph_names)
        elif ph_names:
            names = [f"PH {n}" for n in ph_names]
        elif us_names:
            names = [f"US {n}" for n in us_names]
        else:
            names = []

        extra = _extra_holidays(int(year))
        today_d = date.fromisoformat(today)
        if today_d in extra:
            raw = _norm_holiday(extra[today_d])
            if raw.startswith("US "):
                raw = raw[3:]
            already = raw in ph_names or raw in us_names or raw in names
            already = already or (f"US {raw}" in names) or (f"PH {raw}" in names)
            if not already:
                names.append(f"US {raw}")

        with info_center.lock:
            if names:
                info_center.is_holiday_today = True
                info_center.holiday_name = " / ".join(names)
            else:
                info_center.is_holiday_today = False
                info_center.holiday_name = ""
            info_center.holiday_last_check = time.monotonic()
        return True

    except Exception as e:
        logger.warning("Holiday fetch error: %s", e)
        return False
                
def _safe_get(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=_FETCH_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.warning("Network fetch failed: %s", e)
        return None

def update_indoor_temp():
    c, f = read_temp()
    with info_center.lock:
        info_center.temp_c = c
        info_center.temp_f = f

def _fetcher_loop():
    weather_ok   = False
    quake_ok     = False
    exchange_ok  = False
    oil_ok       = False
    stock_ok     = False
    holiday_ok   = False

    weather_retry  = _FetchRetry("Weather")
    quake_retry    = _FetchRetry("Earthquake")
    exchange_retry = _FetchRetry("Exchange")
    oil_retry      = _FetchRetry("Oil")
    stock_retry    = _FetchRetry("Stocks")
    holiday_retry  = _FetchRetry("Holiday")

    while True:
        try:
            if info_center.power_level == POWER_SLEEP:
                time.sleep(20)
                continue

            now = time.monotonic()

            update_indoor_temp()

            if weather_retry.allow(now) and (
                    not weather_ok or
                    (now - info_center.weather_last_update) >=
                    info_center.weather_update_interval):
                if fetch_weather():
                    weather_ok = True
                    weather_retry.success()
                else:
                    weather_ok = False
                    weather_retry.failure()

            if quake_retry.allow(now) and (
                    not quake_ok or
                    (now - info_center.quake_last_update) >=
                    info_center.quake_update_interval):
                if fetch_earthquake():
                    quake_ok = True
                    quake_retry.success()
                else:
                    quake_ok = False
                    quake_retry.failure()

            if exchange_retry.allow(now) and (
                    not exchange_ok or
                    (now - info_center.exchange_last_update) >=
                    info_center.exchange_update_interval):
                if fetch_exchange():
                    exchange_ok = True
                    exchange_retry.success()
                else:
                    exchange_ok = False
                    exchange_retry.failure()

            if oil_retry.allow(now) and (
                    not oil_ok or
                    (now - info_center.oil_last_update) >=
                    info_center.oil_update_interval):
                if fetch_oil():
                    oil_ok = True
                    oil_retry.success()
                else:
                    oil_ok = False
                    oil_retry.failure()

            if stock_retry.allow(now) and (
                    not stock_ok or
                    (now - info_center.stock_last_update) >=
                    info_center.stock_update_interval):
                if fetch_stocks():
                    stock_ok = True
                    stock_retry.success()
                else:
                    stock_ok = False
                    stock_retry.failure()

            if holiday_retry.allow(now) and (
                    not holiday_ok or
                    (now - info_center.holiday_last_check) >=
                    info_center.holiday_check_interval):
                if fetch_holidays():
                    holiday_ok = True
                    holiday_retry.success()
                else:
                    holiday_ok = False
                    holiday_retry.failure()

        except Exception as e:
            logger.warning("Fetcher loop error: %s", e)

        time.sleep(20)

def start_data_fetcher():
    if info_center.fetcher.started:
        if info_center.debug_mode:
            logger.debug("Data fetcher already running – skipping")
        return

    info_center.fetcher.started = True

    thread = threading.Thread(
        target=_fetcher_loop,
        name="DataFetcher",
        daemon=True
    )
    thread.start()
    logger.info("Background data fetcher thread started")

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
