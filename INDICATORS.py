#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  INDICATORS.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

# Project Imports
from   CONFIG         import info_center
from   PANEL          import strip
from   PANEL          import init_strip
from   PANEL          import set_pixel
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_WHITE
from   PANEL          import update_strip
from   PANEL          import clear_panel
from   PANEL          import get_conversion_value
from   PANEL          import apply_brightness

# Logging
logger = logging.getLogger(__name__)

def _origin():
    return 2 + (info_center.panel_width - 32) // 2
    
def indicate_military_time(erase=False):
    if strip is None or not info_center.power_flag:
        return

    row         = 6
    column      = _origin() + 28
    physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                        info_center.panel_orientation, row, column)

    if erase:
        color_to_use = COLOR_BLACK
    else:
        color_to_use = COLOR_GREEN if info_center.military_time else COLOR_BLACK
            
    if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
        set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))

def indicate_am_or_pm(erase=False):
    if strip is None or not info_center.power_flag:
        return

    row         = 1
    column      = _origin() + 28
    physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                        info_center.panel_orientation, row, column)

    info_center.pm_flag = True
    if ((int(info_center.current_time[0]) * 10) + int(info_center.current_time[1]) < 12):
        info_center.pm_flag = False

    if erase:
        color_to_use = COLOR_BLACK
    else:
        color_to_use = COLOR_PURPLE
        if info_center.military_time or not info_center.pm_flag:
            color_to_use = COLOR_BLACK
            
    if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
        set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))

def indicate_time_colon_and_dot(erase=False):
    if strip is None or not info_center.power_flag:
        return

    color_to_use = COLOR_PURPLE
    if erase or not info_center.colon_flag:
        color_to_use = COLOR_BLACK
            
    # Colon (upper)
    column = _origin() + 8

    row = 2
    physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                        info_center.panel_orientation, row, column)
    if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
        set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))
   
    row = 5
    physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                        info_center.panel_orientation, row, column)
    if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
        set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))
    
    # Seconds dot
    column = _origin() + 18
    
    row = 6
    physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                        info_center.panel_orientation, row, column)
    if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
        set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))

def indicate_date_slashes(erase=False):
    if strip is None or not info_center.power_flag:
        return

    color_to_use = COLOR_PURPLE if not erase else COLOR_BLACK

    column = _origin() + 8
    for row in range(2, 6):
        physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                            info_center.panel_orientation, row, column)
        if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
            set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))

    column = _origin() + 18
    for row in range(2, 6):
        physical_led = get_conversion_value(info_center.panel_width, info_center.panel_height,
                                            info_center.panel_orientation, row, column)
        if physical_led >= info_center.panel_led_start and physical_led <= info_center.panel_led_end:
            set_pixel(physical_led, apply_brightness(color_to_use, info_center.panel_brightness))

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
