#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  EXCHANGE.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

from CONFIG         import info_center
from CONFIG         import LOWER_TEXT_ROW
from DATA_FETCHER   import is_data_fresh
from FONT_3X6       import CHAR_UP_LEFT, CHAR_UP_RIGHT
from FONT_3X6       import CHAR_DOWN_LEFT, CHAR_DOWN_RIGHT
from PANEL          import COLOR_WHITE, COLOR_CYAN, COLOR_BLUE, COLOR_ORANGE
from PANEL          import clear_lower_panel
from PANEL          import continuous_scroll_message

logger = logging.getLogger(__name__)

def _fmt_rate(rate):
    if rate >= 1000:
        return f"{rate:.0f}"
    if rate >= 100:
        return f"{rate:.1f}"
    return f"{rate:.2f}"

def build_exchange_message_and_colors():
    def add(text, color, msg, colors):
        for ch in text:
            msg.append(ch)
            colors.append(color)

    base  = getattr(info_center, "exchange_base", "USD")
    quote = getattr(info_center, "exchange_quote", "PHP")
    rate  = info_center.exchange_rate
    prev  = info_center.last_exchange_rate

    msg, colors = [], []
    add("1", COLOR_CYAN, msg, colors)
    add(base, COLOR_WHITE, msg, colors)
    add(" = ", COLOR_WHITE, msg, colors)
    add(_fmt_rate(rate), COLOR_CYAN, msg, colors)
    add(quote, COLOR_WHITE, msg, colors)
    
    if prev > 0.0:
        if rate > prev:
            add(chr(CHAR_UP_LEFT) + chr(CHAR_UP_RIGHT), COLOR_BLUE, msg, colors)
        elif rate < prev:
            add(chr(CHAR_DOWN_LEFT) + chr(CHAR_DOWN_RIGHT), COLOR_ORANGE, msg, colors)

    return "".join(msg), colors

def display_exchange():
    now = time.monotonic()
    ex = info_center.exchange
    fresh = is_data_fresh(info_center.exchange_last_update, 1800.0)
    need_rebuild = (
        not info_center.pattern_init or
        info_center.exchange_last_update > ex.last_built or
        not fresh
    )

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()
        if not fresh:
            base  = getattr(info_center, "exchange_base", "USD")
            quote = getattr(info_center, "exchange_quote", "PHP")
            msg = "1 %s = --.-- %s" % (base, quote)
            colors = [COLOR_WHITE] * len(msg)
        else:
            msg, colors = build_exchange_message_and_colors()
        ex.msg = msg
        ex.colors = colors
        ex.last_built = info_center.exchange_last_update
        continuous_scroll_message(
            string_to_scroll=msg,
            from_right=True,
            row=LOWER_TEXT_ROW,
            char_colors=colors
        )
        return

    continuous_scroll_message(
        string_to_scroll=ex.msg or "FX OFFLINE",
        from_right=True,
        row=LOWER_TEXT_ROW,
        char_colors=ex.colors or None
    )
    
#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
