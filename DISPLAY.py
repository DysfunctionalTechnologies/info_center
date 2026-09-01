#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  DISPLAY.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import random
import time

# Project Imports
from   CONFIG       import info_center
from   CONFIG       import HOURS_TENS
from   CONFIG       import HOURS_ONES
from   CONFIG       import MINS_TENS
from   CONFIG       import MINS_ONES
from   CONFIG       import SECS_TENS
from   CONFIG       import SECS_ONES
from   CONFIG       import MONTH_TENS
from   CONFIG       import MONTH_ONES
from   CONFIG       import DATE_TENS
from   CONFIG       import DATE_ONES
from   CONFIG       import YEAR_TENS
from   CONFIG       import YEAR_ONES
from   CONFIG       import DISSOLVE_STEP_DELAY
from   CONFIG       import UPPER_PANEL_START_ROW
from   CONFIG       import LOWER_TEXT_ROW
from   CONFIG       import LOWER_PANEL_START_ROW
from   CONFIG       import LOWER_PANEL_END_ROW
from   CONFIG       import PACMAN_Y_OFFSET
from   FONT_3X6     import CHAR_ZERO
from   INDICATORS   import indicate_am_or_pm
from   INDICATORS   import indicate_military_time
from   INDICATORS   import indicate_time_colon_and_dot
from   INDICATORS   import indicate_date_slashes
from   PANEL        import strip
from   PANEL        import COLOR_BLACK
from   PANEL        import COLOR_RED
from   PANEL        import COLOR_YELLOW
from   PANEL        import COLOR_GREEN
from   PANEL        import COLOR_CYAN
from   PANEL        import COLOR_BLUE
from   PANEL        import COLOR_PURPLE
from   PANEL        import COLOR_WHITE
from   PANEL        import print_char
from   PANEL        import print_string
from   PANEL        import clear_upper_panel
from   PANEL        import get_upper_pixels
from   PANEL        import clear_pixel
from   PANEL        import apply_brightness
from   PANEL        import get_conversion_value
from   PANEL        import set_pixel
from   PANEL        import get_char_bitmap

def display_strings(string1_to_display=None,
                    string1_color=COLOR_WHITE,
                    string1_col_offset=0,
                    string1_row=UPPER_PANEL_START_ROW,
                    string1_centered=True,
                    string1_colors=None,
                    string2_to_display=None,
                    string2_color=COLOR_WHITE,
                    string2_col_offset=0,
                    string2_row=LOWER_PANEL_START_ROW,
                    string2_centered=True,
                    string2_colors=None):
    now = time.monotonic()
    if now - info_center.upper.last_string_draw > 0.3:
        if string1_to_display is not None:
            print_string(string1_to_display,
                         column=string1_col_offset,
                         row=string1_row,
                         fg_color=string1_color,
                         char_colors=string1_colors,
                         centered=string1_centered)
        if string2_to_display is not None:
            print_string(string2_to_display,
                         column=string2_col_offset,
                         row=string2_row,
                         fg_color=string2_color,
                         char_colors=string2_colors,
                         centered=string2_centered)
        info_center.upper.last_string_draw = now

def upper_clock_origin():
    return 2 + (info_center.panel_width - 32) // 2

def display_time():
    if info_center.saved_time != info_center.current_time:
        info_center.colon_flag = not info_center.colon_flag
        info_center.saved_time = info_center.current_time

    adjusted_hours = (int(info_center.current_time[HOURS_TENS]) * 10) + int(info_center.current_time[HOURS_ONES])
    if not info_center.military_time:
        if adjusted_hours == 0:
            adjusted_hours = 12
        if adjusted_hours > 12:
            adjusted_hours -= 12

    print_char(CHAR_ZERO + int(adjusted_hours / 10),      COLOR_WHITE, COLOR_BLACK, upper_clock_origin() +  0, UPPER_PANEL_START_ROW)
    print_char(CHAR_ZERO + int(adjusted_hours % 10),      COLOR_WHITE, COLOR_BLACK, upper_clock_origin() +  4, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_time[MINS_TENS]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 10, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_time[MINS_ONES]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 14, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_time[SECS_TENS]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 20, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_time[SECS_ONES]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 24, UPPER_PANEL_START_ROW)

    indicate_time_colon_and_dot()
    indicate_am_or_pm()
    indicate_military_time()

def display_date():
    print_char(ord(info_center.current_date[MONTH_TENS]), COLOR_WHITE, COLOR_BLACK, upper_clock_origin() +  0, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_date[MONTH_ONES]), COLOR_WHITE, COLOR_BLACK, upper_clock_origin() +  4, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_date[DATE_TENS]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 10, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_date[DATE_ONES]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 14, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_date[YEAR_TENS]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 20, UPPER_PANEL_START_ROW)
    print_char(ord(info_center.current_date[YEAR_ONES]),  COLOR_WHITE, COLOR_BLACK, upper_clock_origin() + 24, UPPER_PANEL_START_ROW)

    indicate_date_slashes()

def display_day_of_week():
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    dow_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    day_string = days[dow_map.get(info_center.current_dow, 0)]

    print_string(day_string,
                 column=int((info_center.panel_width - 12) / 2),
                 row=UPPER_PANEL_START_ROW,
                 fg_color=COLOR_WHITE)

def update_upper_panel():
    now = time.monotonic()
    upper = info_center.upper

    # ---------- First-time init ----------
    if not upper.initialized:
        upper.initialized = True
        upper.mode = 0
        upper.pending_mode = 0
        upper.dissolve_phase = 3
        upper.dissolve_pixels = get_upper_pixels()
        random.shuffle(upper.dissolve_pixels)
        upper.dissolve_next = now
        upper.mode_start = 0.0

        upper.holiday_phase  = 0
        upper.holiday_pos    = 0
        upper.holiday_next   = 0.0
        upper.holiday_text   = ""
        upper.holiday_buffer = None
        upper._paused        = False
        upper._pause_done    = False
        clear_upper_panel()

    max_mode = 3 if info_center.is_holiday_today else 2

    # ----- Dissolve state machine -----
    if upper.dissolve_phase == 1:          # OUT
        if now >= upper.dissolve_next:
            batch = upper.dissolve_batch
            for _ in range(min(batch, len(upper.dissolve_pixels))):
                if upper.dissolve_pixels:
                    r, c = upper.dissolve_pixels.pop()
                    clear_pixel(r, c)
            upper.dissolve_next = now + DISSOLVE_STEP_DELAY

            if not upper.dissolve_pixels:
                upper.dissolve_phase = 2
                upper.dissolve_next = now + upper.dissolve_hold

    elif upper.dissolve_phase == 2:        # hold + switch
        if now >= upper.dissolve_next:
            upper.mode = upper.pending_mode
            upper.dissolve_phase = 3
            upper.dissolve_pixels = get_upper_pixels()
            random.shuffle(upper.dissolve_pixels)
            clear_upper_panel()
            upper.dissolve_next = now

            if upper.mode == 3:
                upper.holiday_phase = 1
                upper._paused = False
                upper._pause_done = False

    elif upper.dissolve_phase == 3:        # IN
        if upper.mode == 0:
            display_time()
        elif upper.mode == 1:
            display_date()
        elif upper.mode == 2:
            display_day_of_week()

        for r, c in upper.dissolve_pixels:
            clear_pixel(r, c)

        if now >= upper.dissolve_next:
            batch = upper.dissolve_batch
            for _ in range(min(batch, len(upper.dissolve_pixels))):
                if upper.dissolve_pixels:
                    upper.dissolve_pixels.pop()
            upper.dissolve_next = now + DISSOLVE_STEP_DELAY

            if not upper.dissolve_pixels:
                upper.dissolve_phase = 0
                upper.mode_start = now

    else:   # stable
        if upper.mode != 3:
            duration = upper.durations[upper.mode]
            if now - upper.mode_start >= duration:
                upper.pending_mode = (upper.mode + 1) % (max_mode + 1)
                upper.dissolve_phase = 1
                upper.dissolve_pixels = get_upper_pixels()
                random.shuffle(upper.dissolve_pixels)
                upper.dissolve_next = now

            if upper.mode == 0:
                display_time()
            elif upper.mode == 1:
                display_date()
            elif upper.mode == 2:
                display_day_of_week()
        else:
            _update_holiday_scroll(now)

def _update_holiday_scroll(now):
    """
    Buffer-based holiday scroller (live brightness).
    Sequence:
      1. HOLIDAY (PURPLE) scrolls in from right → centres → pauses 3 s → off left
      2. Full NAME (WHITE) scrolls in from right → completely off left
      3. Dissolve back to TIME
    """
    upper = info_center.upper
    speed = 0.080
    char_w = info_center.font_width + 1

    def build_buffer(text, fg_color):
        text_w = len(text) * char_w
        usable = info_center.panel_width - 2
        buf_w  = text_w + usable * 2 + 8

        buf = [[0 for _ in range(buf_w)] for _ in range(info_center.font_height)]

        x = usable
        for ch in text:
            bitmap = get_char_bitmap(ord(ch))
            for y in range(info_center.font_height):
                for px in range(info_center.font_width):
                    if (bitmap[y] >> (info_center.font_width - 1 - px)) & 1:
                        if 0 <= x + px < buf_w:
                            buf[y][x + px] = fg_color
            x += char_w
        return buf

    def blit(pos, buf):
        buf_w = len(buf[0])
        for y in range(info_center.font_height):
            r = UPPER_PANEL_START_ROW + y
            for c in range(1, info_center.panel_width - 1):
                buf_col = pos + (c - 1)
                raw = buf[y][buf_col] if 0 <= buf_col < buf_w else 0
                color = apply_brightness(raw, info_center.panel_brightness)
                i = get_conversion_value(row=r, column=c)
                if i >= 0:
                    set_pixel(i, color)

    if upper.holiday_phase == 1:
        upper.holiday_text   = "HOLIDAY"
        upper.holiday_buffer = build_buffer("HOLIDAY", COLOR_PURPLE)
        upper.holiday_pos    = 0
        upper.holiday_next   = now
        upper._paused        = False
        upper._pause_done    = False
        upper.holiday_phase  = 2

    elif upper.holiday_phase == 2:
        blit(upper.holiday_pos, upper.holiday_buffer)

        text_w = 7 * char_w
        usable = info_center.panel_width - 2
        centre = usable - (usable - text_w) // 2

        if upper.holiday_pos < centre:
            if now >= upper.holiday_next:
                upper.holiday_pos += 1
                upper.holiday_next = now + speed

        elif not upper._paused and not upper._pause_done:
            upper.holiday_pos = centre
            upper._paused = True
            upper.holiday_next = now + 3.0

        elif upper._paused:
            if now >= upper.holiday_next:
                upper._paused = False
                upper._pause_done = True
                upper.holiday_next = now + speed

        else:
            if now >= upper.holiday_next:
                upper.holiday_pos += 1
                upper.holiday_next = now + speed

                if upper.holiday_pos >= len(upper.holiday_buffer[0]) - usable:
                    upper.holiday_phase = 3
                    upper._paused = False
                    upper._pause_done = False

    elif upper.holiday_phase == 3:
        name = (info_center.holiday_name or "HOLIDAY").strip().upper()
        upper.holiday_text   = name
        upper.holiday_buffer = build_buffer(name, COLOR_WHITE)
        upper.holiday_pos    = 0
        upper.holiday_next   = now
        upper.holiday_phase  = 4

    elif upper.holiday_phase == 4:
        if now >= upper.holiday_next:
            blit(upper.holiday_pos, upper.holiday_buffer)

            upper.holiday_pos += 1
            upper.holiday_next = now + speed

            usable = info_center.panel_width - 2
            if upper.holiday_pos >= len(upper.holiday_buffer[0]) - usable:
                upper.pending_mode = 0
                upper.dissolve_phase = 1
                upper.dissolve_pixels = get_upper_pixels()
                random.shuffle(upper.dissolve_pixels)
                upper.dissolve_next = now
                upper.holiday_phase = 0
                upper._paused = False
                upper._pause_done = False

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
