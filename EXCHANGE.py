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
import random
import time

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import DISSOLVE_STEP_DELAY
from   CONFIG         import EXCHANGE_DISSOLVE_BATCH
from   CONFIG         import EXCHANGE_HOLD_TIME
from   CONFIG         import EXCHANGE_ALERT_MINOR
from   CONFIG         import LOWER_PANEL_START_ROW
from   CONFIG         import LOWER_PANEL_END_ROW
from   CONFIG         import LOWER_TEXT_ROW
from   DATA_FETCHER   import is_data_fresh
from   FONT_3X6       import CHAR_PERIOD
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
from   PANEL          import get_conversion_value
from   PANEL          import strip
from   PANEL          import print_char
from   PANEL          import print_string
from   PANEL          import set_pixel

logger = logging.getLogger(__name__)

def get_lower_pixels():
    pixels = []
    for r in range(LOWER_PANEL_START_ROW, LOWER_PANEL_END_ROW):
        for c in range(1, info_center.panel_width - 1):
            pixels.append((r, c))
    return pixels

def clear_lower_pixel(row, col):
    i = get_conversion_value(row=row, column=col)
    if info_center.panel_led_start <= i <= info_center.panel_led_end:
        set_pixel(i, COLOR_BLACK)


def _snapshot_arrow():
    ex = info_center.exchange
    rate = info_center.exchange_rate
    prev = info_center.last_exchange_rate
    ex.arrow = None
    if prev > 0.0:
        delta = abs(rate - prev)
        if delta >= EXCHANGE_ALERT_MINOR:
            if rate > prev:
                ex.arrow = "up"
            elif rate < prev:
                ex.arrow = "down"

def draw_exchange_rate():
    ex = info_center.exchange
    rate = info_center.exchange_rate

    rate_str = f"{rate:.2f}"
    int_part, frac_part = rate_str.split('.')

    char_w   = info_center.font_width + 1
    period_w = 2

    show_arrow  = ex.arrow in ("up", "down")
    arrow_chars = None
    arrow_color = COLOR_WHITE

    if ex.arrow == "up":
        arrow_chars = (130, 131)
        arrow_color = COLOR_BLUE
    elif ex.arrow == "down":
        arrow_chars = (132, 133)
        arrow_color = COLOR_ORANGE

    total_width = (
        char_w +
        len(int_part) * char_w +
        period_w +
        2 * char_w
    )
    if show_arrow:
        total_width += (info_center.font_width * 2)

    start_col = (info_center.panel_width - total_width) // 2
    if start_col < 1:
        start_col = 1

    col = start_col

    print_char(ord('P'), COLOR_WHITE, COLOR_BLACK, col, LOWER_TEXT_ROW)
    col += char_w

    for ch in int_part:
        print_char(ord(ch), COLOR_CYAN, COLOR_BLACK, col, LOWER_TEXT_ROW)
        col += char_w

    print_char(CHAR_PERIOD, COLOR_WHITE, COLOR_BLACK, col, LOWER_TEXT_ROW)
    col += period_w

    print_char(ord(frac_part[0]), COLOR_CYAN, COLOR_BLACK, col, LOWER_TEXT_ROW)
    col += char_w
    if len(frac_part) > 1:
        print_char(ord(frac_part[1]), COLOR_CYAN, COLOR_BLACK, col, LOWER_TEXT_ROW)
        col += char_w

    if show_arrow:
        print_char(arrow_chars[0], arrow_color, COLOR_BLACK, col, LOWER_TEXT_ROW, tight=True)
        col += info_center.font_width
        print_char(arrow_chars[1], arrow_color, COLOR_BLACK, col, LOWER_TEXT_ROW, tight=True)

def display_exchange():
    now = time.monotonic()
    ex = info_center.exchange

    fresh = is_data_fresh(info_center.exchange_last_update, 1800.0)

    if not fresh:
        if not info_center.pattern_init:
            info_center.pattern_init = True
            clear_lower_panel()
            info_center.pattern_end_time = now + 8.0

        print_string("FX --.--",
                     row=LOWER_TEXT_ROW,
                     fg_color=COLOR_WHITE,
                     centered=True)
        return

    if not info_center.pattern_init:
        info_center.pattern_init = True
        _snapshot_arrow()
        ex.dissolve_phase = 3
        ex.dissolve_pixels = get_lower_pixels()
        random.shuffle(ex.dissolve_pixels)
        ex.dissolve_next = now
        ex.hold_start = 0.0
        clear_lower_panel()
        info_center.pattern_end_time = now + 15.0
        return

    if ex.dissolve_phase in (0, 1, 3):
        info_center.pattern_end_time = now + 10.0

    if ex.dissolve_phase == 1:          # OUT
        if now >= ex.dissolve_next:
            batch = EXCHANGE_DISSOLVE_BATCH
            for _ in range(min(batch, len(ex.dissolve_pixels))):
                if ex.dissolve_pixels:
                    r, c = ex.dissolve_pixels.pop()
                    clear_lower_pixel(r, c)
            ex.dissolve_next = now + DISSOLVE_STEP_DELAY

            if not ex.dissolve_pixels:
                clear_lower_panel()
                ex.dissolve_phase = 4
                info_center.pattern_end_time = now + 0.4
                ex.hold_start = 0.0

    elif ex.dissolve_phase == 3:        # IN
        draw_exchange_rate()

        for r, c in ex.dissolve_pixels:
            clear_lower_pixel(r, c)

        if now >= ex.dissolve_next:
            batch = EXCHANGE_DISSOLVE_BATCH
            for _ in range(min(batch, len(ex.dissolve_pixels))):
                if ex.dissolve_pixels:
                    ex.dissolve_pixels.pop()
            ex.dissolve_next = now + DISSOLVE_STEP_DELAY

            if not ex.dissolve_pixels:
                ex.dissolve_phase = 0
                ex.hold_start = now

    elif ex.dissolve_phase == 0:        # HOLD – same arrow as dissolve-in
        draw_exchange_rate()

        if (ex.hold_start > 0 and
            (now - ex.hold_start) >= EXCHANGE_HOLD_TIME):
            ex.dissolve_phase = 1
            ex.dissolve_pixels = get_lower_pixels()
            random.shuffle(ex.dissolve_pixels)
            ex.dissolve_next = now
            ex.hold_start = 0.0
            
    elif ex.dissolve_phase == 4:
        pass

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
