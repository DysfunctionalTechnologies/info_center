#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  OIL.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import LOWER_TEXT_ROW
from   DATA_FETCHER   import is_data_fresh
from   FONT_3X6       import CHAR_UP_LEFT
from   FONT_3X6       import CHAR_UP_RIGHT
from   FONT_3X6       import CHAR_DOWN_LEFT
from   FONT_3X6       import CHAR_DOWN_RIGHT
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_WHITE
from   PANEL          import COLOR_ORANGE
from   PANEL          import clear_lower_panel
from   PANEL          import continuous_scroll_message

logger = logging.getLogger(__name__)

def _fmt_price(usd):
    """Return (usd_str, php_str) with 2 decimals"""
    php = usd * info_center.exchange_rate
    return f"{usd:.2f}", f"{php:.2f}"

def build_oil_message_and_colors():
    def add(text, color, msg, colors):
        for ch in text:
            msg.append(ch)
            colors.append(color)

    def add_arrow(usd_value, prev_value, msg, colors):
        """Returns True if an arrow was added"""
        if prev_value > 0.0:
            if usd_value > prev_value:
                add(chr(CHAR_UP_LEFT),  COLOR_BLUE,   msg, colors)
                add(chr(CHAR_UP_RIGHT), COLOR_BLUE,   msg, colors)
                return True
            elif usd_value < prev_value:
                add(chr(CHAR_DOWN_LEFT),  COLOR_ORANGE, msg, colors)
                add(chr(CHAR_DOWN_RIGHT), COLOR_ORANGE, msg, colors)
                return True
        return False

    def add_price(usd_value, msg, colors):
        usd_str, php_str = _fmt_price(usd_value)

        # $xx.xx
        add("$", COLOR_WHITE, msg, colors)
        int_part, frac = usd_str.split('.')
        add(int_part, COLOR_CYAN, msg, colors)
        add(".", COLOR_WHITE, msg, colors)
        add(frac, COLOR_CYAN, msg, colors)

        add("/", COLOR_WHITE, msg, colors)

        # Pxx.xx
        add("P", COLOR_WHITE, msg, colors)
        int_part, frac = php_str.split('.')
        add(int_part, COLOR_CYAN, msg, colors)
        add(".", COLOR_WHITE, msg, colors)
        add(frac, COLOR_CYAN, msg, colors)

    msg = []
    colors = []

    add("CRUDE OIL: ", COLOR_WHITE, msg, colors)

    # WTI
    add("WTI", COLOR_WHITE, msg, colors)
    had_arrow = add_arrow(info_center.oil_wti, info_center.prev_wti, msg, colors)
    if not had_arrow:
        add(" ", COLOR_WHITE, msg, colors)
    add_price(info_center.oil_wti, msg, colors)
    add(", ", COLOR_WHITE, msg, colors)

    # BRENT
    add("BRENT", COLOR_WHITE, msg, colors)
    had_arrow = add_arrow(info_center.oil_brent, info_center.prev_brent, msg, colors)
    if not had_arrow:
        add(" ", COLOR_WHITE, msg, colors)
    add_price(info_center.oil_brent, msg, colors)
    add(", ", COLOR_WHITE, msg, colors)

    # URALS
    add("URALS", COLOR_WHITE, msg, colors)
    had_arrow = add_arrow(info_center.oil_urals, info_center.prev_urals, msg, colors)
    if not had_arrow:
        add(" ", COLOR_WHITE, msg, colors)
    add_price(info_center.oil_urals, msg, colors)

    return "".join(msg), colors

def display_oil():
    now = time.monotonic()
    oil = info_center.oil

    fresh = is_data_fresh(info_center.oil_last_update, 1800.0)

    first_paint = not info_center.pattern_init
    oil_tick    = info_center.oil_last_update > oil.last_built
    fx_tick     = info_center.exchange_last_update > oil.last_built

    need_rebuild = (
        first_paint or
        oil_tick or
        fx_tick or
        not fresh
    )

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()

        if not fresh:
            msg = "OIL OFFLINE"
            colors = [COLOR_WHITE] * len(msg)
        else:
            msg, colors = build_oil_message_and_colors()

        oil.msg        = msg
        oil.colors     = colors
        oil.last_built = max(info_center.oil_last_update,
                             info_center.exchange_last_update)

        continuous_scroll_message(
            string_to_scroll=msg,
            from_right=True,
            row=LOWER_TEXT_ROW,
            char_colors=colors
        )
        return

    continuous_scroll_message(
        string_to_scroll=oil.msg or "OIL OFFLINE",
        from_right=True,
        row=LOWER_TEXT_ROW,
        char_colors=oil.colors or None
    )

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
