#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  WEATHER.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

# Project Imports
from   CONFIG       import info_center
from   CONFIG       import LOWER_TEXT_ROW
from   DATA_FETCHER import is_data_fresh
from   FONT_3X6     import CHAR_DEGREE
from   FONT_3X6     import CHAR_SUN_LEFT
from   FONT_3X6     import CHAR_SUN_RIGHT
from   FONT_3X6     import CHAR_MOON_LEFT
from   FONT_3X6     import CHAR_MOON_RIGHT
from   PANEL        import COLOR_BLACK
from   PANEL        import COLOR_RED
from   PANEL        import COLOR_YELLOW
from   PANEL        import COLOR_GREEN
from   PANEL        import COLOR_CYAN
from   PANEL        import COLOR_BLUE
from   PANEL        import COLOR_PURPLE
from   PANEL        import COLOR_WHITE
from   PANEL        import COLOR_GREY
from   PANEL        import TRANSPARENT
from   PANEL        import clear_lower_panel
from   PANEL        import continuous_scroll_message

logger = logging.getLogger(__name__)

WMO_CODES = {
    0: "CLEAR",
    1: "MAINLY CLEAR",
    2: "PARTLY CLOUDY",
    3: "OVERCAST",
    45: "FOG",
    48: "FOG",
    51: "DRIZZLE",
    53: "DRIZZLE",
    55: "DRIZZLE",
    61: "RAIN",
    63: "RAIN",
    65: "HEAVY RAIN",
    71: "SNOW",
    73: "SNOW",
    75: "HEAVY SNOW",
    80: "SHOWERS",
    81: "SHOWERS",
    82: "HEAVY SHOWERS",
    95: "THUNDER",
    96: "THUNDER",
    99: "THUNDER",
}

def degrees_to_compass(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((deg + 22.5) // 45) % 8]
    
def build_weather_message_and_colors():
    def add(text, color, msg_chars, colors):
        for ch in text:
            msg_chars.append(ch)
            colors.append(color)

    def add_number(number_str, msg_chars, colors):
        """Digits = cyan, everything else = white"""
        for ch in number_str:
            if ch.isdigit():
                add(ch, COLOR_CYAN, msg_chars, colors)
            else:
                add(ch, COLOR_WHITE, msg_chars, colors)

    if info_center.weather_is_day:
        icon_left, icon_right = CHAR_SUN_LEFT, CHAR_SUN_RIGHT
        icon_color = COLOR_YELLOW
    else:
        icon_left, icon_right = CHAR_MOON_LEFT, CHAR_MOON_RIGHT
        icon_color = COLOR_WHITE

    if info_center.alert_level == 2:
        alert_color = COLOR_RED
    elif info_center.alert_level == 1:
        alert_color = COLOR_YELLOW
    else:
        alert_color = None

    msg_chars = []
    colors    = []

    add(chr(icon_left),  icon_color, msg_chars, colors)
    add(chr(icon_right), icon_color, msg_chars, colors)

    loc = (info_center.weather_location or "").strip().upper()
    add(loc if loc else "UNKNOWN", COLOR_CYAN, msg_chars, colors)
    add("-", COLOR_WHITE, msg_chars, colors)

    use_c = bool(getattr(info_center, "temp_celsius", True))
    unit = "C" if use_c else "F"

    def add_one_temp(temp_c, temp_f):
        t = temp_c if use_c else temp_f
        sign = "-" if t < 0 else "+"
        whole = int(abs(t))
        frac = int(round((abs(t) - whole) * 10)) % 10
        add(sign, COLOR_WHITE, msg_chars, colors)
        add_number(f"{whole}.{frac}", msg_chars, colors)
        add(chr(CHAR_DEGREE) + unit, COLOR_WHITE, msg_chars, colors)

    add("IN/OUT:", COLOR_WHITE, msg_chars, colors)
    add_one_temp(info_center.temp_c, info_center.temp_f)
    add("/", COLOR_WHITE, msg_chars, colors)
    add_one_temp(info_center.weather_temp_c, info_center.weather_temp_f)
    add(", ", COLOR_WHITE, msg_chars, colors)

    add("WIND:", COLOR_WHITE, msg_chars, colors)
    add_number(f"{info_center.weather_wind_kmh:.0f}", msg_chars, colors)
    add("KPH, ", COLOR_WHITE, msg_chars, colors)

    add("GUSTS:", COLOR_WHITE, msg_chars, colors)
    add_number(f"{info_center.weather_wind_gusts:.0f}", msg_chars, colors)
    add("KPH, ", COLOR_WHITE, msg_chars, colors)

    add("DIR:", COLOR_WHITE, msg_chars, colors)
    compass = degrees_to_compass(info_center.weather_wind_dir)
    info_center.weather_wind_compass = compass
    add(compass, COLOR_CYAN, msg_chars, colors)
    add(", ", COLOR_WHITE, msg_chars, colors)

    add("RH:", COLOR_WHITE, msg_chars, colors)
    add_number(f"{info_center.weather_humidity}", msg_chars, colors)
    add("%, ", COLOR_WHITE, msg_chars, colors)

    desc = WMO_CODES.get(info_center.weather_code, "UNKNOWN")
    info_center.weather_description = desc
    add(desc, alert_color if alert_color else COLOR_CYAN, msg_chars, colors)
            
    return "".join(msg_chars), colors

def display_weather():
    now = time.monotonic()
    wx = info_center.weather

    fresh = is_data_fresh(info_center.weather_last_update, 1800.0)

    need_rebuild = (
        not info_center.pattern_init or
        info_center.weather_last_update > wx.last_built or
        not fresh
    )

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()

        if not fresh:
            msg = "WEATHER OFFLINE"
            colors = [COLOR_WHITE] * len(msg)
        else:
            msg, colors = build_weather_message_and_colors()

        wx.msg        = msg
        wx.colors     = colors
        wx.last_built = info_center.weather_last_update

        continuous_scroll_message(
            string_to_scroll=msg,
            from_right=True,
            row=LOWER_TEXT_ROW,
            char_colors=colors
        )
        return

    continuous_scroll_message(
        string_to_scroll=wx.msg or "WEATHER OFFLINE",
        from_right=True,
        row=LOWER_TEXT_ROW,
        char_colors=wx.colors or None
    )

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
