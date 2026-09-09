#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  PANEL.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import threading
import time
from   RPI_WS281X import create_strip

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import MIN_BRIGHTNESS
from   CONFIG         import MAX_BRIGHTNESS
from   CONFIG         import BRIGHTNESS_STEP
from   CONFIG         import PANEL_DAYTIME_BRIGHTNESS
from   CONFIG         import PANEL_NIGHTTIME_BRIGHTNESS
from   CONFIG         import UPPER_PANEL_START_ROW
from   CONFIG         import UPPER_PANEL_END_ROW
from   CONFIG         import LOWER_PANEL_START_ROW
from   CONFIG         import LOWER_PANEL_END_ROW
from   CONFIG         import LOWER_TEXT_ROW
from   CONFIG         import BORDER_INSET
from   CONFIG         import NETWORK_GOOD
from   CONFIG         import NETWORK_BAD
from   CONFIG         import NETWORK_PROBLEM
from   CONFIG         import POWER_ON
from   CONFIG         import POWER_BLACKOUT
from   CONFIG         import POWER_SLEEP
from   CONFIG         import ALERT_FLASH_INTERVAL
from   CONFIG         import PANEL_LAYOUT
from   DATA_FETCHER   import is_data_fresh
from   EEPROM         import eeprom
from   EEPROM         import save_persisted
from   FONT_3X6       import FONT
from   FONT_3X6       import FONT_HEIGHT
from   FONT_3X6       import FONT_WIDTH

# Logging
logger = logging.getLogger(__name__)

# Thread-safe printing + LED buffer lock
print_lock = threading.Lock()
strip_lock = threading.RLock()

# Dirty flag – only push to hardware when something changed
strip_dirty            = False
brightness_dirty       = False
last_brightness_change = 0.0

# Pre-computed conversion lookup table
_conversion_table = None

# Color Defines
COLOR_BLACK                   = 0x000000
COLOR_RED                     = 0xFF0000
COLOR_YELLOW                  = 0xFFFF00
COLOR_GREEN                   = 0x00FF00
COLOR_CYAN                    = 0x00FFFF
COLOR_BLUE                    = 0x0000FF
COLOR_PURPLE                  = 0xFF00FF
COLOR_WHITE                   = 0xFFFFFF
COLOR_PINK                    = 0xFF69B4
COLOR_ORANGE                  = 0xFF8000
COLOR_BLUE_FRIGHTENED         = 0x0000AA
COLOR_GREY                    = 0x808080
TRANSPARENT                   = -1

# Brightness EEPROM debounce
BRIGHTNESS_SAVE_DEBOUNCE = 2.5          # seconds of stability before writing

# Initialize strip
try:
    strip = create_strip(
        info_center.total_led_count,
        info_center.strip_gpio,
        info_center.strip_freq,
        info_center.strip_dma,
        info_center.strip_invert,
        info_center.strip_brightness,
        info_center.strip_channel
    )
except Exception as e:
    with print_lock:
        print(f"Error initializing NeoPixel: {e}")
    strip = None

def set_pixel(led_index, color):
    """Single point that writes a pixel and marks the strip dirty."""
    global strip_dirty
    if strip is None:
        return
    strip.setPixelColor(led_index, color)
    strip_dirty = True

def mark_dirty():
    global strip_dirty
    strip_dirty = True

def apply_brightness(color, brightness=None):
    if brightness is None:
        brightness = info_center.panel_brightness

    if not info_center.power_flag:
        return 0

    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    factor = brightness / MAX_BRIGHTNESS
    return ((int(r * factor) << 16) | (int(g * factor) << 8) | int(b * factor))

def update_brightness():
    global brightness_dirty, last_brightness_change

    if info_center.auto_brightness:
        if is_data_fresh(info_center.weather_last_update, 1800.0):
            daytime = bool(info_center.weather_is_day)
        else:
            h = int(time.strftime("%H", time.localtime()))
            daytime = not (h < 6 or h >= 18)

        target = (info_center.day_brightness
                  if daytime else info_center.night_brightness)
        info_center.day_time = daytime

        if info_center.panel_brightness != target:
            info_center.panel_brightness = target
            brightness_dirty = True
            last_brightness_change = time.monotonic()
            mark_dirty()

    if brightness_dirty:
        now = time.monotonic()
        if (now - last_brightness_change) >= BRIGHTNESS_SAVE_DEBOUNCE:
            _save_brightness_settings()
            brightness_dirty = False
            if info_center.debug_mode:
                logger.info("Brightness settings saved (debounced) → %s",
                            info_center.panel_brightness)

def brightness_up():
    global brightness_dirty, last_brightness_change

    if strip is None:
        return

    new_brightness = min(info_center.panel_brightness + BRIGHTNESS_STEP, MAX_BRIGHTNESS)

    if new_brightness != info_center.panel_brightness:
        info_center.auto_brightness = False
        info_center.panel_brightness = new_brightness
        brightness_dirty = True
        last_brightness_change = time.monotonic()
        mark_dirty()
        if info_center.debug_mode:
            logger.info("Brightness increased: Panel=%s", info_center.panel_brightness)

def brightness_down():
    global brightness_dirty, last_brightness_change

    if strip is None:
        return

    new_brightness = max(info_center.panel_brightness - BRIGHTNESS_STEP, MIN_BRIGHTNESS)

    if new_brightness != info_center.panel_brightness:
        info_center.auto_brightness = False
        info_center.panel_brightness = new_brightness
        brightness_dirty = True
        last_brightness_change = time.monotonic()
        mark_dirty()
        if info_center.debug_mode:
            logger.info("Brightness decreased: Panel=%s", info_center.panel_brightness)

def _save_brightness_settings():
    save_persisted()

def power_off():
    if strip is None:
        return

    if info_center.power_level == POWER_ON:
        info_center.power_level = POWER_BLACKOUT
        info_center.power_flag = False
        clear_panel()
        update_strip()

    elif info_center.power_level == POWER_BLACKOUT:
        info_center.power_level = POWER_SLEEP

def power_on():
    if strip is None:
        return
    info_center.power_level = POWER_ON
    info_center.power_flag = True
    mark_dirty()

def led_index_8x32_pair(row, column):
    if row >= 8:
        if column % 2 == 0:
            loc = row - 8
        else:
            loc = 15 - row
        return column * 8 + loc
    from_right = 31 - column
    if from_right % 2 == 0:
        loc = 7 - row
    else:
        loc = row
    return 256 + from_right * 8 + loc
    
def _calculate_conversion(width, height, orientation, row, column, inverse=False):
    if not (0 <= row < height and 0 <= column < width):
        return -1
    if width <= 0 or height <= 0:
        return -1

    if getattr(info_center, "panel_layout", None) == "8x32" or PANEL_LAYOUT == "8x32":
        return led_index_8x32_pair(row, column)
        
    if orientation == 0:
        new_row, new_col, new_width, new_height = row, column, width, height
    elif orientation == 180:
        new_row = height - 1 - row
        new_col = width - 1 - column
        new_width, new_height = width, height
    elif orientation == 90:
        new_row = width - 1 - column
        new_col = height - 1 - row
        new_width, new_height = height, width
    elif orientation == 270:
        new_row = column
        new_col = height - 1 - row
        new_width, new_height = height, width
    else:
        return -1

    col_index = new_width - 1 - new_col if inverse else new_col

    if col_index % 2 == 0:
        index = col_index * new_height + new_row
    else:
        index = col_index * new_height + (new_height - 1 - new_row)

    if not (0 <= index < info_center.panel_led_count):
        return -1

    final_index = index + info_center.panel_led_start
    if not (info_center.panel_led_start <= final_index <= info_center.panel_led_end):
        return -1

    return final_index

def build_conversion_table():
    global _conversion_table

    width  = info_center.panel_width
    height = info_center.panel_height
    orient = info_center.panel_orientation

    table = [[-1 for _ in range(width)] for _ in range(height)]

    for row in range(height):
        for col in range(width):
            table[row][col] = _calculate_conversion(width, height, orient, row, col)

    _conversion_table = table

    if info_center.debug_mode:
        logger.info("Conversion table built (%sx%s, orient=%s)", width, height, orient)

def get_conversion_value(width=None, height=None, orientation=None, row=0, column=0, inverse=False):
    global _conversion_table

    if width is None:
        width = info_center.panel_width
    if height is None:
        height = info_center.panel_height
    if orientation is None:
        orientation = info_center.panel_orientation

    if (_conversion_table is not None and
        width == info_center.panel_width and
        height == info_center.panel_height and
        orientation == info_center.panel_orientation and
        not inverse):

        if 0 <= row < height and 0 <= column < width:
            return _conversion_table[row][column]
        return -1

    return _calculate_conversion(width, height, orientation, row, column, inverse)

def init_strip():
    if strip is None:
        return
    strip.begin()
    build_conversion_table()
    clear_panel()
    update_strip()

def clear_panel():
    if strip is None:
        return
    set_panel(COLOR_BLACK)
    clear_globe()

def set_panel(panel_color=COLOR_BLACK):
    if strip is None:
        return
    color_wipe_panel(panel_color)

def clear_upper_panel():
    if strip is None:
        return
    bg_color = COLOR_BLACK
    for r in range(UPPER_PANEL_START_ROW, UPPER_PANEL_END_ROW + 1):
        for c in range(BORDER_INSET, info_center.panel_width - BORDER_INSET):
            i = get_conversion_value(row=r, column=c)
            if i >= 0:
                set_pixel(i, bg_color)

def clear_lower_panel():
    if strip is None:
        return
    bg_color = COLOR_BLACK
    for r in range(LOWER_PANEL_START_ROW, LOWER_PANEL_END_ROW):
        for c in range(BORDER_INSET, info_center.panel_width - BORDER_INSET):
            i = get_conversion_value(row=r, column=c)
            if i >= 0:
                set_pixel(i, bg_color)

def clear_both_panels():
    if strip is None:
        return
    bg_color = COLOR_BLACK
    for r in range(UPPER_PANEL_START_ROW, LOWER_PANEL_END_ROW):
        for c in range(BORDER_INSET, info_center.panel_width - BORDER_INSET):
            i = get_conversion_value(row=r, column=c)
            if i >= 0:
                set_pixel(i, bg_color)

def get_upper_pixels():
    pixels = []
    for r in range(UPPER_PANEL_START_ROW, UPPER_PANEL_END_ROW + 1):
        for c in range(BORDER_INSET, info_center.panel_width - BORDER_INSET):
            pixels.append((r, c))
    return pixels

def clear_pixel(row, col):
    i = get_conversion_value(row=row, column=col)
    if i >= info_center.panel_led_start and i <= info_center.panel_led_end:
        set_pixel(i, COLOR_BLACK)

def update_strip():
    """Push data to the LEDs only when something changed."""
    global strip_dirty

    if strip is None:
        return

    if not strip_dirty:
        return

    with strip_lock:
        try:
            strip.show()
            strip_dirty = False
        except Exception:
            pass

def strip_cleanup():
    """Turn every LED off and release the strip as cleanly as possible."""
    if strip is None:
        return
    try:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, 0)
        strip.show()
    except Exception:
        pass

    try:
        if hasattr(strip, "_cleanup"):
            strip._cleanup()
    except Exception:
        pass

def color_wipe_panel(color):
    if strip is None:
        return
    color = apply_brightness(color, info_center.panel_brightness)
    with strip_lock:
        for i in range(info_center.panel_led_start, info_center.panel_led_end + 1):
            set_pixel(i, color)

def print_char(char, fg_color=COLOR_WHITE, bg_color=COLOR_BLACK,
               column=0, row=0, tight=False):
    if strip is None:
        return

    char_width = info_center.font_width if tight else (info_center.font_width + 1)

    if (column < 1 or
        column + char_width - 1 > info_center.panel_width - 2 or
        row < 1 or
        row + info_center.font_height - 1 > info_center.panel_height - 2):
        return

    fg = apply_brightness(fg_color, info_center.panel_brightness)
    bg = apply_brightness(bg_color, info_center.panel_brightness)

    for y in range(info_center.font_height):
        r = row + y
        for x in range(char_width):
            c = column + x
            i = get_conversion_value(row=r, column=c)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                if x < info_center.font_width and get_pixel(char, y, x):
                    set_pixel(i, fg)
                else:
                    set_pixel(i, bg)

def print_string(text, column=0, row=0,
                 fg_color=COLOR_WHITE, bg_color=COLOR_BLACK,
                 char_colors=None, centered=False, tight_space=False):
    if strip is None or not text:
        return

    if char_colors is None:
        colors = [fg_color] * len(text)
    else:
        colors = [char_colors[i % len(char_colors)] for i in range(len(text))]

    total_width = 0
    for ch in text:
        if ch == ' ' and tight_space:
            total_width += 2
        else:
            total_width += info_center.font_width + 1

    if centered:
        start_col = (info_center.panel_width - total_width) // 2 + column
    else:
        start_col = column

    if start_col < 0:
        start_col = 0

    x = start_col
    for i, ch in enumerate(text):
        is_tight = ord(ch) in (130, 132, 134, 136)

        if ch == ' ' and tight_space:
            x += 2
            continue

        print_char(ord(ch), colors[i], bg_color, x, row, tight=is_tight)

        if is_tight:
            x += info_center.font_width
        else:
            x += info_center.font_width + 1

def scroll_message(text, row=1, fg_color=COLOR_WHITE, bg_color=COLOR_BLACK,
                   speed=None, hold_time=2.5, tight_space=False):
    if speed is None:
        speed = info_center.scroll.speed

    if strip is None or not text:
        info_center.pattern_end_time = time.monotonic()
        return

    now = time.monotonic()
    sc = info_center.scroll

    def get_char_advance(ch):
        return 2 if (ch == ' ' and tight_space) else (info_center.font_width + 1)

    if not info_center.pattern_init:
        info_center.pattern_init = True
        sc.phase      = 1
        sc.text       = text
        sc.row        = row
        sc.speed      = speed
        sc.tight      = tight_space
        sc.bg         = apply_brightness(bg_color, info_center.panel_brightness)
        sc.fg_list    = [apply_brightness(fg_color, info_center.panel_brightness)] * len(text)

        text_width = sum(get_char_advance(ch) for ch in text)
        sc.text_width = text_width

        usable_width = info_center.panel_width - 2
        buffer_width = text_width + usable_width * 2 + 4

        sc.buffer = [[sc.bg for _ in range(buffer_width)]
                     for _ in range(info_center.font_height)]

        x = usable_width
        for ch in text:
            bitmap = get_char_bitmap(ord(ch))
            for y in range(info_center.font_height):
                for px in range(info_center.font_width):
                    if (bitmap[y] >> (info_center.font_width - 1 - px)) & 1:
                        if 0 <= x + px < buffer_width:
                            sc.buffer[y][x + px] = sc.fg_list[0]
            x += get_char_advance(ch)

        sc.pos = 0
        sc.next = now
        sc.hold_until = 0
        sc.center_pos = usable_width - (usable_width - text_width) // 2
        info_center.pattern_end_time = now + 60.0
        return

    if sc.phase < 4:
        info_center.pattern_end_time = now + 5.0

    usable_width = info_center.panel_width - 2
    buffer = sc.buffer
    buf_w  = len(buffer[0])

    def blit_buffer_window():
        for y in range(info_center.font_height):
            r = sc.row + y
            for c in range(1, info_center.panel_width - 1):
                buf_col = sc.pos + (c - 1)
                color = buffer[y][buf_col] if 0 <= buf_col < buf_w else sc.bg

                i = get_conversion_value(row=r, column=c)
                if info_center.panel_led_start <= i <= info_center.panel_led_end:
                    set_pixel(i, color)

    if sc.phase == 1:
        if now >= sc.next:
            blit_buffer_window()
            sc.pos += 1
            sc.next = now + sc.speed

            if sc.pos >= sc.center_pos:
                sc.phase = 2
                sc.hold_until = now + hold_time

    elif sc.phase == 2:
        if now >= sc.hold_until:
            sc.phase = 3
            sc.next = now

    elif sc.phase == 3:
        if now >= sc.next:
            blit_buffer_window()
            sc.pos += 1
            sc.next = now + sc.speed

            if sc.pos >= buf_w - usable_width:
                sc.phase = 4
                clear_lower_panel()
                info_center.pattern_end_time = now + 0.3

def continuous_scroll_message(string_to_scroll=None,
                              from_right=True,
                              delay=None,
                              row=8,
                              fg_color=COLOR_WHITE,
                              bg_color=COLOR_BLACK,
                              char_colors=None,
                              icon=None,
                              icon_gap=2):
    if delay is None:
        delay = info_center.scroll.speed

    if strip is None:
        info_center.pattern_end_time = time.monotonic()
        return

    if not string_to_scroll:
        if info_center.debug_mode:
            logger.info("continuous_scroll_message: empty string – aborting")
        info_center.pattern_end_time = time.monotonic()
        return

    now = time.monotonic()
    sc = info_center.scroll

    if (sc.text != string_to_scroll or not info_center.pattern_init):
        info_center.pattern_init = False

    if not info_center.pattern_init:
        info_center.pattern_init = True
        sc.phase       = 1
        sc.text        = string_to_scroll
        sc.row         = row
        sc.speed       = delay
        sc.from_right  = from_right
        sc.icon        = icon
        sc.icon_gap    = icon_gap

        if char_colors is None:
            colors = [fg_color] * len(string_to_scroll)
        else:
            colors = [char_colors[i % len(char_colors)] for i in range(len(string_to_scroll))]

        sc.fg_list = colors[:]
        sc.bg      = bg_color

        char_advance = info_center.font_width + 1
        text_width   = 0

        icon_width = 6 if icon is not None else 0
        total_content_width = icon_width + (icon_gap if icon else 0) + len(string_to_scroll) * char_advance

        usable_width = info_center.panel_width - 2
        buffer_width = total_content_width + usable_width * 2 + 4

        sc.buffer = [[sc.bg for _ in range(buffer_width)]
                     for _ in range(info_center.font_height)]

        x = usable_width
        if icon is not None:
            for y in range(6):
                for px in range(6):
                    color = icon[y][px]
                    if color != -1:
                        if 0 <= x + px < buffer_width:
                            sc.buffer[y][x + px] = color
            x += 6 + icon_gap

        for idx, ch in enumerate(string_to_scroll):
            bitmap = get_char_bitmap(ord(ch))
            fg = sc.fg_list[idx]

            if idx > 0 and string_to_scroll[idx-1] == '.':
                x -= 2

            for y in range(info_center.font_height):
                for px in range(info_center.font_width):
                    if (bitmap[y] >> (info_center.font_width - 1 - px)) & 1:
                        if 0 <= x + px < buffer_width:
                            sc.buffer[y][x + px] = fg

            if ord(ch) in (130, 132, 134, 136):
                x += info_center.font_width
            else:
                x += char_advance

        if from_right:
            sc.pos = 0
        else:
            sc.pos = buffer_width - usable_width

        sc.next = now
        info_center.pattern_end_time = now + 90.0
        return

    if sc.phase < 3:
        info_center.pattern_end_time = now + 5.0

    usable_width = info_center.panel_width - 2
    buffer = sc.buffer
    buf_w  = len(buffer[0])

    def blit_buffer_window():
        for y in range(info_center.font_height):
            r = sc.row + y
            for c in range(1, info_center.panel_width - 1):
                buf_col = sc.pos + (c - 1)
                raw = buffer[y][buf_col] if 0 <= buf_col < buf_w else sc.bg
                color = apply_brightness(raw, info_center.panel_brightness)

                i = get_conversion_value(row=r, column=c)
                if info_center.panel_led_start <= i <= info_center.panel_led_end:
                    set_pixel(i, color)

    if sc.phase == 1:
        if now >= sc.next:
            blit_buffer_window()

            if sc.from_right:
                sc.pos += 1
                if sc.pos >= buf_w - usable_width:
                    sc.phase = 2
            else:
                sc.pos -= 1
                if sc.pos <= 0:
                    sc.phase = 2

            sc.next = now + sc.speed

    elif sc.phase == 2:
        clear_lower_panel()
        sc.phase = 3
        info_center.pattern_end_time = now + 0.3

def get_char_bitmap(char):
    raw = FONT.get(char, [0, 0, 0, 0, 0, 0])
    return [int(x) for x in raw]

def get_pixel(char, row, col):
    if not (0 <= row < info_center.font_height and 0 <= col < info_center.font_width):
        return 0
    bitmap = get_char_bitmap(char)
    return (bitmap[row] >> (info_center.font_width - 1 - col)) & 1

def draw_border(border_color=None):
    if strip is None:
        return

    if border_color is None:
        if info_center.internet_status == NETWORK_BAD:
            border_color = COLOR_RED
        elif info_center.internet_status == NETWORK_PROBLEM:
            border_color = COLOR_YELLOW
        elif info_center.internet_status == NETWORK_GOOD:
            border_color = COLOR_GREEN
        else:
            border_color = COLOR_BLUE

    fg_color = apply_brightness(border_color, info_center.panel_brightness)

    for r in range(info_center.panel_height):
        i = get_conversion_value(row=r, column=0)
        if i >= 0:
            set_pixel(i, fg_color)
        i = get_conversion_value(row=r, column=info_center.panel_width - 1)
        if i >= 0:
            set_pixel(i, fg_color)

    for c in range(info_center.panel_width):
        i = get_conversion_value(row=0, column=c)
        if i >= 0:
            set_pixel(i, fg_color)
        i = get_conversion_value(row=info_center.panel_height - 1, column=c)
        if i >= 0:
            set_pixel(i, fg_color)

    draw_globe()

def clear_globe():
    """Force every globe LED completely off."""
    if strip is None:
        return
    for i in range(info_center.globe_led_start, info_center.globe_led_end + 1):
        set_pixel(i, COLOR_BLACK)

def draw_globe():
    """
    Draw the status globe.
    Always black when not POWER_ON.
    Full brightness (no panel brightness applied) when POWER_ON.
    High alert: flash RED
    Low alert:  flash YELLOW
    Both:       RED → YELLOW → BLACK → RED
    """
    if strip is None:
        return

    if info_center.power_level != POWER_ON:
        clear_globe()
        return

    now = time.monotonic()
    high = now < getattr(info_center, "alert_high_until", 0.0)
    low  = now < getattr(info_center, "alert_low_until", 0.0)

    if not high and not low and info_center.alert_level > 0 and now < info_center.alert_until:
        if info_center.alert_level >= 2:
            high = True
        else:
            low = True

    if high or low:
        info_center.alert_level = 2 if high else 1
        info_center.alert_until = max(
            getattr(info_center, "alert_high_until", 0.0),
            getattr(info_center, "alert_low_until", 0.0),
            info_center.alert_until
        )
        step = int(now / max(ALERT_FLASH_INTERVAL, 0.1))
        if high and low:
            globe_color = (COLOR_RED, COLOR_YELLOW, COLOR_BLACK)[step % 3]
        elif high:
            globe_color = COLOR_RED if (step % 2 == 0) else COLOR_BLACK
        else:
            globe_color = COLOR_YELLOW if (step % 2 == 0) else COLOR_BLACK
    else:
        info_center.alert_level = 0

        if info_center.internet_status == NETWORK_BAD:
            globe_color = COLOR_RED
        elif info_center.internet_status == NETWORK_PROBLEM:
            globe_color = COLOR_YELLOW
        elif info_center.internet_status == NETWORK_GOOD:
            globe_color = COLOR_GREEN
        else:
            globe_color = COLOR_BLUE

    for i in range(info_center.globe_led_start, info_center.globe_led_end + 1):
        set_pixel(i, globe_color)

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
