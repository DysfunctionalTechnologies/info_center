#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  INFO_CENTER.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import threading
import time
import os
import sys

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import FRAME_INTERVAL
from   CONFIG         import COLOR_PANEL_SHOW_TIME
from   CONFIG         import COLOR_PANEL_FINAL_HOLD
from   CONFIG         import PROGRAM_NAME_DURATION
from   CONFIG         import COPYRIGHT_DURATION
from   CONFIG         import INTERNET_MONITOR_DURATION
from   CONFIG         import NETWORK_GOOD
from   CONFIG         import NETWORK_BAD
from   CONFIG         import NETWORK_PROBLEM
from   CONFIG         import POWER_BLACKOUT
from   CONFIG         import POWER_SLEEP
from   DATA_FETCHER   import start_data_fetcher
from   DIAGNOSTICS    import diagnostics
from   DISPLAY        import display_strings
from   DISPLAY        import update_upper_panel
from   EARTHQUAKE     import display_earthquake
from   EXCHANGE       import display_exchange
from   GLOBE_LINK     import push_globe
from   IMONITOR       import display_internet_monitor
from   OIL            import display_oil
from   PACMAN         import display_pacman
from   PANEL          import strip
from   PANEL          import init_strip
from   PANEL          import update_strip
from   PANEL          import strip_cleanup
from   PANEL          import set_pixel
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_WHITE
from   PANEL          import clear_panel
from   PANEL          import set_panel
from   PANEL          import draw_border
from   PANEL          import clear_upper_panel
from   PANEL          import clear_lower_panel
from   PANEL          import clear_both_panels
from   PANEL          import update_brightness
from   STOCKS         import display_stocks
from   WEATHER        import display_weather
from   WEB            import start_web

# Centralized Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple software watchdog
last_heartbeat          = 0.0
WATCHDOG_TIMEOUT        = 20.0          # seconds without a pet → restart
WATCHDOG_CHECK_INTERVAL = 5.0

def pet_watchdog():
    global last_heartbeat
    last_heartbeat = time.monotonic()

def _watchdog_loop():
    global last_heartbeat
    while True:
        time.sleep(WATCHDOG_CHECK_INTERVAL)
        now = time.monotonic()
        if last_heartbeat > 0.0 and (now - last_heartbeat) > WATCHDOG_TIMEOUT:
            logger.error(
                f"WATCHDOG TIMEOUT – main loop frozen for "
                f"{now - last_heartbeat:.1f}s → restarting process"
            )
            try:
                strip_cleanup()
            except Exception:
                pass
            # Hard exit so systemd / your launch script can restart us
            os.execv(sys.executable, [sys.executable] + sys.argv)

def start_watchdog():
    global last_heartbeat
    last_heartbeat = time.monotonic()
    t = threading.Thread(target=_watchdog_loop, name="Watchdog", daemon=True)
    t.start()
    logger.info(f"Software watchdog started (timeout={WATCHDOG_TIMEOUT}s)")

# Pattern handler functions
def pattern_color_panels():
    colors = [
        (COLOR_BLACK, "BLACK"),
        (COLOR_RED,   "RED"),
        (COLOR_GREEN, "GREEN"),
        (COLOR_BLUE,  "BLUE"),
        (COLOR_WHITE, "WHITE"),
    ]
    show_time  = COLOR_PANEL_SHOW_TIME
    final_hold = COLOR_PANEL_FINAL_HOLD

    now = time.monotonic()
    cp  = info_center.color          # convenience alias

    if not info_center.pattern_init:
        info_center.pattern_init     = True
        cp.phase                     = 0
        cp.next                      = now
        info_center.pattern_end_time = now + 30.0
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: COLOR PANELS (BLACK, RED, GREEN, BLUE, WHITE)")
        return

    if cp.phase < 6:
        info_center.pattern_end_time = now + 5.0

    if now >= cp.next and cp.phase < 6:
        if cp.phase < len(colors):
            colour, name = colors[cp.phase]
            set_panel(colour)
            cp.phase += 1
            cp.next   = now + show_time
        else:
            clear_panel()
            cp.phase                     = 6
            info_center.pattern_end_time = now + final_hold

def pattern_program_name():
    if not info_center.pattern_init:
        info_center.pattern_init = True
        info_center.pattern_end_time = time.monotonic() + PROGRAM_NAME_DURATION
        clear_both_panels()
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: {info_center.program_name_1_string} {info_center.program_name_2_string}")
    display_strings(string1_to_display=info_center.program_name_1_string,
                    string1_row=1,
                    string1_centered=True,
                    string1_colors=[COLOR_RED, COLOR_WHITE, COLOR_BLUE],
                    string2_to_display=info_center.program_name_2_string,
                    string2_row=8,
                    string2_centered=True,
                    string2_colors=[COLOR_BLUE, COLOR_RED, COLOR_WHITE])

def pattern_copyright():
    if not info_center.pattern_init:
        info_center.pattern_init = True
        info_center.pattern_end_time = time.monotonic() + COPYRIGHT_DURATION
        clear_both_panels()
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: VERSION / COPYRIGHT")
    display_strings(string1_to_display=info_center.version_string,
                    string1_row=1,
                    string1_centered=True,
                    string1_colors=[COLOR_RED, COLOR_WHITE, COLOR_BLUE, COLOR_WHITE, COLOR_WHITE],
                    string2_to_display=info_center.copyright_string,
                    string2_row=8,
                    string2_centered=True,
                    string2_colors=[COLOR_WHITE, COLOR_WHITE, COLOR_WHITE, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE])

def pattern_clear_upper():
    if not info_center.pattern_init:
        info_center.pattern_init = True
        info_center.pattern_end_time = time.monotonic() + 0.01
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: CLEAR UPPER PANEL")
    clear_upper_panel()

def pattern_clear_lower():
    if not info_center.pattern_init:
        info_center.pattern_init = True
        info_center.pattern_end_time = time.monotonic() + 0.01
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: CLEAR LOWER PANEL")
    clear_lower_panel()

def pattern_pacman():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: PAC-MAN CHASE")
    display_pacman()

def pattern_earthquake():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: EARTHQUAKE")
    display_earthquake()

def pattern_exchange():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: EXCHANGE RATE")
    display_exchange()

def pattern_oil():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: CRUDE OIL")
    display_oil()

def pattern_internet_monitor():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: IMONITOR")
    display_internet_monitor(duration=INTERNET_MONITOR_DURATION)

def pattern_weather():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info(f"Pattern {info_center.current_pattern}: WEATHER")
    display_weather()

def pattern_stocks():
    if not info_center.pattern_init:
        if info_center.debug_mode:
            logger.info("Pattern %s: STOCKS", info_center.current_pattern)
    display_stocks()

# Pattern handlers
PATTERN_HANDLERS = [
    None,                           #  0 – unused
    pattern_color_panels,           #  1
    pattern_program_name,           #  2
    pattern_copyright,              #  3
    pattern_clear_upper,            #  4
    pattern_clear_lower,            #  5
    pattern_internet_monitor,       #  6  ← LOOP_START
    pattern_pacman,                 #  7
    pattern_weather,                #  8
    pattern_exchange,               #  9
    pattern_oil,                    # 10
    pattern_stocks,                 # 11
    pattern_earthquake,             # 12
]

LOOP_START = 6

PATTERN_ALWAYS_ON = {6}   # internet monitor only
PATTERN_ENABLE_ATTR = {
    7:  "show_pacman",
    8:  "show_weather",
    9:  "show_exchange",
    10: "show_oil",
    11: "show_stocks",
    12: "show_earthquake",
}

def pattern_allowed(num):
    if num < LOOP_START:
        return True
    if num in PATTERN_ALWAYS_ON:
        return True
    attr = PATTERN_ENABLE_ATTR.get(num)
    if attr is None:
        return True
    return bool(getattr(info_center, attr, True))

def next_loop_pattern(current):
    cycle_len = len(PATTERN_HANDLERS) - LOOP_START
    nxt = current
    for _ in range(max(1, cycle_len)):
        nxt = LOOP_START + ((nxt - LOOP_START + 1) % cycle_len)
        if pattern_allowed(nxt):
            return nxt
    return LOOP_START
    
def main():
    logger.info("#-----------------------------------------#")
    logger.info("# INFO CENTER (C)2026, Timothy S. Carlson #")
    logger.info("#           All Rights Reserved           #")
    logger.info("#    With technical assistance by Grok    #")
    logger.info("#          Thank you, Elon Musk!          #")
    logger.info("#-----------------------------------------#")
    
    if info_center.debug_mode:
        logger.info(f"\n{info_center.program_name_1_string} {info_center.program_name_2_string} Program Started (Version {info_center.version_string})")
        logger.info(f"Panel: {info_center.panel_height}x{info_center.panel_width}")
        logger.info("----------------------------------------")

    init_strip()
    clear_panel()
    time.sleep(0.3)

    # Start background services (always)
    start_data_fetcher()
    start_web()
    start_watchdog()

    info_center.pattern_init     = False
    info_center.current_pattern  = 0
    info_center.pattern_end_time = time.monotonic()
    last_frame_time              = time.monotonic()
    frame_interval               = FRAME_INTERVAL

    try:
        while True:
            now = time.monotonic()
            # Pet the watchdog every frame to stay alive
            # always, including BLACKOUT / SLEEP
            pet_watchdog()
            
            if getattr(info_center, "diag_busy", False):
                time.sleep(0.05)
                continue            

            # ----- Power handling -----
            if info_center.power_level == POWER_BLACKOUT:
                # Soft: screen black, but everything else continues
                clear_panel()
                update_strip()
                time.sleep(0.05)
                continue

            if info_center.power_level == POWER_SLEEP:
                # Hard: screen black + pause almost all activity
                clear_panel()
                update_strip()
                time.sleep(0.25)          # slower wake-up check
                continue

            # Normal operation continues below...
            update_brightness()

            if info_center.current_pattern != 1:
                draw_border()

            info_center.current_time = time.strftime("%H%M%S", time.localtime())
            info_center.current_date = time.strftime("%m%d%y", time.localtime())
            info_center.current_dow  = time.strftime("%a", time.localtime()).upper()

            # ----- Advance pattern -----
            # Drop a disabled pattern immediately (scrolls keep extending end_time)
            if (info_center.current_pattern >= LOOP_START and
                    not pattern_allowed(info_center.current_pattern)):
                info_center.current_pattern = next_loop_pattern(
                    info_center.current_pattern)
                info_center.pattern_init = False
                info_center.pattern_end_time = now + 0.05

            elif now >= info_center.pattern_end_time:
                if info_center.current_pattern >= LOOP_START:
                    info_center.current_pattern = next_loop_pattern(
                        info_center.current_pattern)
                else:
                    info_center.current_pattern += 1
                info_center.pattern_init = False
                info_center.pattern_end_time = now + 0.05
                                
            # ----- Dispatch -----
            if 1 <= info_center.current_pattern < len(PATTERN_HANDLERS):
                PATTERN_HANDLERS[info_center.current_pattern]()
            else:
                if info_center.debug_mode:
                    logger.info(f"- Unexpected pattern {info_center.current_pattern} – resetting to {LOOP_START}")
                info_center.current_pattern = LOOP_START
                info_center.pattern_init = False
                info_center.pattern_end_time = now + 0.2

            # ===== Independent upper panel rotation =====
            if info_center.current_pattern >= LOOP_START:
                update_upper_panel()
            # ============================================

            # ============================================
            # to keep from overwrite diag panels
            # ============================================
            if getattr(info_center, "diag_busy", False):
                time.sleep(0.05)
                continue

            # ===== SINGLE UPDATE FOR THE WHOLE FRAME =====
            update_strip()
            # =============================================

            push_globe()
            
            elapsed = time.monotonic() - last_frame_time
            time.sleep(max(0.001, frame_interval - elapsed))
            last_frame_time = time.monotonic()
            
    except KeyboardInterrupt:
        logger.info("Interrupted by Ctrl-C")
    except Exception:
        logger.exception("Error in main")
    finally:
        logger.info("Cleaning up...")
        clear_panel()
        if strip:
            try:
                strip_cleanup()
            except Exception:
                logger.exception("strip_cleanup failed")
        logger.info("Program terminated.")

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    main()
#----------------------------------------------------------#
