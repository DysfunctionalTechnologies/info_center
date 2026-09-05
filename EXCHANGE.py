#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 5, 2026
# Module:  EXCHANGE.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

from   CONFIG         import info_center
from   CONFIG         import LOWER_TEXT_ROW
from   DATA_FETCHER   import is_data_fresh
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_WHITE
from   PANEL          import clear_lower_panel
from   PANEL          import continuous_scroll_message

logger = logging.getLogger(__name__)

def build_exchange_message_and_colors():
    def add(text, color, msg, colors):
        for ch in text:
            msg.append(ch)
            colors.append(color)

    primary   = getattr(info_center, "exchange_primary", "USD")
    secondary = getattr(info_center, "exchange_secondary", "PHP")
    ok_p = bool(getattr(info_center, "primary_valid", True))
    ok_s = bool(getattr(info_center, "secondary_valid", True))
    pair = float(getattr(info_center, "pair_rate", 0.0) or 0.0)

    if ok_p and ok_s and pair > 0.0:
        rate_str = f"{pair:.2f}" if pair >= 0.1 else f"{pair:.4f}"
        rate_color = COLOR_CYAN
    else:
        rate_str = "--.--"
        rate_color = COLOR_RED

    msg, colors = [], []
    add("1", COLOR_CYAN, msg, colors)
    add(primary, COLOR_WHITE if ok_p else COLOR_RED, msg, colors)
    add("=", COLOR_WHITE, msg, colors)
    add(rate_str, rate_color, msg, colors)
    add(secondary, COLOR_WHITE if ok_s else COLOR_RED, msg, colors)
    return "".join(msg), colors

def display_exchange():
    ex = info_center.exchange
    fresh = is_data_fresh(info_center.exchange_last_update, 1800.0)
    first_paint = not info_center.pattern_init
    fx_tick = info_center.exchange_last_update > ex.last_built
    need_rebuild = first_paint or fx_tick

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()
        if not fresh:
            msg, colors = "FX OFFLINE", [COLOR_WHITE] * 10
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
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
