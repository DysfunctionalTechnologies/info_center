#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  DIAGNOSTICS.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import socket
import time

# Project Imports
from   CONFIG         import info_center
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_WHITE
from   PANEL          import apply_brightness
from   PANEL          import clear_panel
from   PANEL          import color_wipe_panel
from   PANEL          import get_conversion_value
from   PANEL          import init_strip
from   PANEL          import print_char
from   PANEL          import set_pixel
from   PANEL          import strip
from   PANEL          import strip_cleanup
from   PANEL          import update_strip
import INDICATORS     as _ind
from   TEMPERATURE    import read_temp

DIAG_BRIGHTNESS = 63

logger = logging.getLogger(__name__)

def _diag_log(msg):
    print(msg)
    logger.info(msg)

def _fill_panel(color):
    for row in range(info_center.panel_height):
        for col in range(info_center.panel_width):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, apply_brightness(color, DIAG_BRIGHTNESS))
    update_strip()
    update_strip()

def test_site(site):
    host = site
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0]
    host = host.split(":", 1)[0]
    if not host:
        return False
    try:
        socket.create_connection((host, 80), timeout=3).close()
        return True
    except OSError:
        try:
            socket.create_connection((host, 443), timeout=3).close()
            return True
        except OSError:
            return False

def display_panel_diagnostic():
    _diag_log("Testing RGB Matrix...")
    init_strip()
    clear_panel()
    update_strip()
    time.sleep(0.15)
    update_strip()

    _diag_log("Panel fill RED")
    _fill_panel(COLOR_RED)
    time.sleep(2)
    _diag_log("Panel fill GREEN")
    _fill_panel(COLOR_GREEN)
    time.sleep(2)
    _diag_log("Panel fill BLUE")
    _fill_panel(COLOR_BLUE)
    time.sleep(2)
    _diag_log("Panel fill WHITE")
    _fill_panel(COLOR_WHITE)
    time.sleep(2)

    _diag_log("Horizontal Lines...")
    clear_panel()
    update_strip()
    for row in range(info_center.panel_height):
        for col in range(info_center.panel_width):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, apply_brightness(COLOR_YELLOW, DIAG_BRIGHTNESS))
        update_strip()
        time.sleep(0.05)
        update_strip()
        time.sleep(0.25)
        for col in range(info_center.panel_width):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, COLOR_BLACK)
        update_strip()
        time.sleep(0.05)
        update_strip()
    time.sleep(0.5)

    _diag_log("Vertical Lines...")
    clear_panel()
    update_strip()
    for col in range(info_center.panel_width):
        for row in range(info_center.panel_height):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, apply_brightness(COLOR_CYAN, DIAG_BRIGHTNESS))
        update_strip()
        time.sleep(0.05)
        update_strip()
        time.sleep(0.25)
        for row in range(info_center.panel_height):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, COLOR_BLACK)
        update_strip()
        time.sleep(0.05)
        update_strip()
    time.sleep(0.5)
    
    _diag_log("Checkerboard (purple)...")
    clear_panel()
    for row in range(info_center.panel_height):
        for col in range(info_center.panel_width):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                if (row + col) % 2 == 0:
                    set_pixel(i, apply_brightness(COLOR_PURPLE, DIAG_BRIGHTNESS))
                else:
                    set_pixel(i, COLOR_BLACK)
    update_strip()
    time.sleep(2)

    _diag_log("Inverse Checkerboard (green)...")
    clear_panel()
    for row in range(info_center.panel_height):
        for col in range(info_center.panel_width):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                if (row + col) % 2 == 0:
                    set_pixel(i, COLOR_BLACK)
                else:
                    set_pixel(i, apply_brightness(COLOR_GREEN, DIAG_BRIGHTNESS))
    update_strip()
    time.sleep(2)

    _diag_log("Horizontal Color Bands...")
    colors = [COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW,
              COLOR_CYAN, COLOR_PURPLE, COLOR_WHITE]
    band_height = max(1, info_center.panel_height // len(colors))
    clear_panel()
    for idx, color in enumerate(colors):
        start_row = idx * band_height
        end_row = start_row + band_height
        if idx == len(colors) - 1:
            end_row = info_center.panel_height
        for row in range(start_row, end_row):
            for col in range(info_center.panel_width):
                i = get_conversion_value(info_center.panel_width,
                                         info_center.panel_height,
                                         info_center.panel_orientation,
                                         row, col)
                if info_center.panel_led_start <= i <= info_center.panel_led_end:
                    set_pixel(i, apply_brightness(color, DIAG_BRIGHTNESS))
    update_strip()
    time.sleep(3)

    _diag_log("Vertical Color Bands (2-col R/G/B/Y/C/P/grey/W)...")
    color_grey = apply_brightness(COLOR_WHITE, 64)
    vcolors = [COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW,
               COLOR_CYAN, COLOR_PURPLE, color_grey, COLOR_WHITE]
    clear_panel()
    for col in range(info_center.panel_width):
        color = vcolors[(col // 2) % len(vcolors)]
        for row in range(info_center.panel_height):
            i = get_conversion_value(info_center.panel_width,
                                     info_center.panel_height,
                                     info_center.panel_orientation,
                                     row, col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, apply_brightness(color, DIAG_BRIGHTNESS))
    update_strip()
    time.sleep(3)

    clear_panel()
    update_strip()
    _diag_log("Panel diagnostic done.")

def display_indicator_diagnostic():
    _diag_log("Testing Indicators...")
    init_strip()
    clear_panel()
    update_strip()
    time.sleep(0.05)
    update_strip()

    saved_military = info_center.military_time
    saved_colon    = getattr(info_center, "colon_flag", True)
    saved_time     = getattr(info_center, "current_time", "120000")
    saved_power    = info_center.power_flag

    info_center.power_flag = True

    _diag_log("AM/PM ON...")
    info_center.military_time = False
    info_center.current_time = "150000"
    _ind.indicate_am_or_pm(False)
    update_strip()
    time.sleep(2)
    _ind.indicate_am_or_pm(True)
    update_strip()
    time.sleep(1)

    _diag_log("Military Time ON...")
    info_center.military_time = True
    _ind.indicate_military_time(False)
    update_strip()
    time.sleep(2)
    _ind.indicate_military_time(True)
    update_strip()
    time.sleep(1)

    _diag_log("Colon ON...")
    info_center.colon_flag = True
    _ind.indicate_time_colon_and_dot(False)
    update_strip()
    time.sleep(2)
    _ind.indicate_time_colon_and_dot(True)
    update_strip()
    time.sleep(1)

    _diag_log("Date Slash ON...")
    _ind.indicate_date_slashes(False)
    update_strip()
    time.sleep(2)
    _ind.indicate_date_slashes(True)
    update_strip()
    time.sleep(1)

    info_center.military_time = saved_military
    info_center.colon_flag    = saved_colon
    info_center.current_time  = saved_time
    info_center.power_flag    = saved_power

    clear_panel()
    update_strip()

def display_font_diagnostic():
    _diag_log("Testing Font...")
    init_strip()
    clear_panel()
    update_strip()
    time.sleep(0.15)
    update_strip()
    
    font_w = info_center.font_width
    width  = info_center.panel_width
    chars_per_row = 7
    step = 4
    used = (chars_per_row - 1) * step + font_w
    start_col = max(1, (width - used) // 2)
    row_top = 1
    row_bot = 9

    test_chars = []
    for c in range(ord('0'), ord('9') + 1):
        test_chars.append(c)
    for c in range(ord('A'), ord('Z') + 1):
        test_chars.append(c)
    test_chars.extend([
        ord('-'), ord(':'), ord('/'), ord('.'), ord(' '),
        127,
        128, 129,
        130, 131, 132, 133,
        134, 135, 136, 137,
    ])
    
    per_page = chars_per_row * 2
    for start in range(0, len(test_chars), per_page):
        clear_panel()
        page = test_chars[start:start + per_page]
        top = page[:chars_per_row]
        bot = page[chars_per_row:]
        for i, char_code in enumerate(top):
            print_char(char_code, COLOR_WHITE, COLOR_BLACK,
                       start_col + i * step, row_top)
        for i, char_code in enumerate(bot):
            print_char(char_code, COLOR_WHITE, COLOR_BLACK,
                       start_col + i * step, row_bot)
        update_strip()
        time.sleep(2)

    clear_panel()
    update_strip()

def display_temperature_diagnostic():
    _diag_log("Testing Temperature Sensor...")
    for n in range(1, 11):
        c, f = read_temp()
        msg = f"  [{n}/10] Temperature: {c:.1f} C / {f:.1f} F"
        print(msg)
        logger.info(msg)
        time.sleep(1)
    _diag_log("Temperature diagnostic done.")

def display_internet_diagnostic():
    _diag_log("Testing Internet Connectivity...")
    init_strip()
    clear_panel()
    update_strip()

    for site in info_center.internet_test_sites:
        result = test_site(site)
        status = "OK" if result else "FAIL"
        msg = f"  {site}: {status}"
        print(msg)
        logger.info(msg)

    time.sleep(2)
    clear_panel()
    update_strip()

diagnostics = {
    1: display_panel_diagnostic,
    2: display_indicator_diagnostic,
    3: display_font_diagnostic,
    4: display_temperature_diagnostic,
    5: display_internet_diagnostic,
}

def show_diagnostic_menu():
    init_strip()

    print("Info Center Diagnostics")
    print("1. Panel Diagnostic")
    print("2. Indicator Diagnostic")
    print("3. Font Diagnostic")
    print("4. Temperature Diagnostic")
    print("5. Internet Diagnostic")
    print("6. Toggle Debug Mode")
    print("0. Run Main Program")
    print("Q. Quit")

    run_main = False
    while True:
        choice = input("Select: ").strip().upper()
        if choice == "Q":
            break
        if choice == "6":
            info_center.debug_mode = not info_center.debug_mode
            print(f"Debug mode: {info_center.debug_mode}")
            continue
        if choice == "0":
            run_main = True
            break
        try:
            n = int(choice)
        except ValueError:
            continue
        if n in diagnostics:
            diagnostics[n]()

    if not run_main:
        clear_panel()
        update_strip()
        strip_cleanup()
    return run_main

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    from DATA_FETCHER import start_data_fetcher
    start_data_fetcher()

    if show_diagnostic_menu():
        from INFO_CENTER import main
        main()
#----------------------------------------------------------#
