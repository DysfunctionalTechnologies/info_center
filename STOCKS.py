#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 5, 2026
# Module:  STOCKS.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

# Project Imports
from CONFIG       import info_center
from CONFIG       import LOWER_TEXT_ROW
from DATA_FETCHER import is_data_fresh
from DATA_FETCHER import fetch_stocks
from FONT_3X6     import CHAR_UP_LEFT, CHAR_UP_RIGHT, CHAR_DOWN_LEFT, CHAR_DOWN_RIGHT
from PANEL        import COLOR_RED, COLOR_CYAN, COLOR_WHITE, COLOR_BLUE, COLOR_ORANGE
from PANEL        import clear_lower_panel, continuous_scroll_message

logger = logging.getLogger(__name__)

def _primary_symbol(code):
    if code == "USD":
        return "$"
    if code == "PHP":
        return "P"
    return ""

def build_stocks_message_and_colors():
    def add(text, color, msg, colors):
        for ch in text:
            msg.append(ch)
            colors.append(color)

    symbols = list(getattr(info_center, "stock_symbols", []))
    prices  = list(getattr(info_center, "stock_prices", []))
    prevs   = list(getattr(info_center, "stock_prevs", []))
    flags   = list(getattr(info_center, "stock_valid", []))
    factor  = float(getattr(info_center, "usd_to_primary", 0.0) or 0.0)
    primary = getattr(info_center, "exchange_primary", "USD")
    prim_ok = bool(getattr(info_center, "primary_valid", True))
    symch   = _primary_symbol(primary)

    msg, colors = [], []
    add("STOCKS:", COLOR_WHITE, msg, colors)
    any_sym = False

    for i, raw in enumerate(symbols):
        ticker = (raw or "").strip().upper()
        if not ticker:
            continue
        any_sym = True
        if msg[-1] != ":":
            add(" ", COLOR_WHITE, msg, colors)
        ok = bool(flags[i]) if i < len(flags) else False
        usd = float(prices[i]) if i < len(prices) else 0.0
        prev = float(prevs[i]) if i < len(prevs) else 0.0
        val = usd * factor if (ok and factor > 0.0) else 0.0
        add(ticker, COLOR_WHITE if ok else COLOR_RED, msg, colors)
        if ok and prev > 0.0 and usd != prev:
            if usd > prev:
                add(chr(CHAR_UP_LEFT), COLOR_BLUE, msg, colors)
                add(chr(CHAR_UP_RIGHT), COLOR_BLUE, msg, colors)
            elif usd < prev:
                add(chr(CHAR_DOWN_LEFT), COLOR_ORANGE, msg, colors)
                add(chr(CHAR_DOWN_RIGHT), COLOR_ORANGE, msg, colors)
        body = f"{val:.2f}" if (ok and prim_ok and val > 0.0) else "--.--"
        int_part, frac = body.split(".")
        code_color = COLOR_WHITE if (ok and prim_ok) else COLOR_RED
        num_color  = COLOR_CYAN if (ok and prim_ok and val > 0.0) else COLOR_RED
        if symch:
            add(symch, code_color, msg, colors)
        else:
            add(primary, code_color, msg, colors)
        add(int_part, num_color, msg, colors)
        add(".", COLOR_WHITE, msg, colors)
        add(frac, num_color, msg, colors)

    if not any_sym:
        return "STOCKS:NONE", [COLOR_WHITE] * 11
    return "".join(msg), colors

def display_stocks():
    st = info_center.stocks
    fresh = is_data_fresh(info_center.stock_last_update, 1800.0)
    first_paint = not info_center.pattern_init
    tick = info_center.stock_last_update > st.last_built
    fx_tick = info_center.exchange_last_update > st.last_built
    need_rebuild = first_paint or tick or fx_tick

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()
        if not fresh:
            msg, colors = "STOCKS OFFLINE", [COLOR_WHITE] * 14
        else:
            msg, colors = build_stocks_message_and_colors()
        st.msg = msg
        st.colors = colors
        st.last_built = max(info_center.stock_last_update,
                            info_center.exchange_last_update)
        continuous_scroll_message(
            string_to_scroll=msg, from_right=True,
            row=LOWER_TEXT_ROW, char_colors=colors)
        return

    continuous_scroll_message(
        string_to_scroll=st.msg or "STOCKS OFFLINE",
        from_right=True, row=LOWER_TEXT_ROW,
        char_colors=st.colors or None)
        
#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
