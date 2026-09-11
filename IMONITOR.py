#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  IMONITOR.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import subprocess
import threading
import time
import logging

logger = logging.getLogger(__name__)

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import LOWER_TEXT_ROW
from   CONFIG         import NETWORK_UNTESTED
from   CONFIG         import NETWORK_GOOD
from   CONFIG         import NETWORK_PROBLEM
from   CONFIG         import NETWORK_BAD
from   FONT_3X6       import CHAR_THINI
from   FONT_3X6       import CHAR_N
from   FONT_3X6       import CHAR_T
from   FONT_3X6       import CHAR_E
from   FONT_3X6       import CHAR_R
from   FONT_3X6       import CHAR_THINE
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_BLUE
from   PANEL          import print_char
from   PANEL          import clear_lower_panel

TOTAL_PINGS = 2 * len(info_center.internet_test_sites)

ping_status = [NETWORK_UNTESTED] * TOTAL_PINGS

_ping_lock = threading.Lock()
_ping_gen  = 0
_ping_done = False
_end_armed = False

def _counts():
    d = info_center.ping_counts
    for site in info_center.internet_test_sites:
        if site not in d:
            d[site] = {"bad": 0, "total": 0}
    return d
    
def status_to_color(status):
    if status == NETWORK_BAD:
        return COLOR_RED
    if status == NETWORK_PROBLEM:
        return COLOR_YELLOW
    if status == NETWORK_GOOD:
        return COLOR_GREEN
    return COLOR_BLUE

def update_internet_panel():
    start_row = LOWER_TEXT_ROW
    start_col = int((info_center.panel_width / 2) - 16)

    print_char(CHAR_THINI, status_to_color(ping_status[0]), COLOR_BLACK, start_col + 2,  start_row)
    print_char(CHAR_N,     status_to_color(ping_status[1]), COLOR_BLACK, start_col + 4,  start_row)
    print_char(CHAR_T,     status_to_color(ping_status[2]), COLOR_BLACK, start_col + 8,  start_row)
    print_char(CHAR_E,     status_to_color(ping_status[3]), COLOR_BLACK, start_col + 12, start_row)
    print_char(CHAR_R,     status_to_color(ping_status[4]), COLOR_BLACK, start_col + 16, start_row)
    print_char(CHAR_N,     status_to_color(ping_status[5]), COLOR_BLACK, start_col + 20, start_row)
    print_char(CHAR_THINE, status_to_color(ping_status[6]), COLOR_BLACK, start_col + 24, start_row)
    print_char(CHAR_T,     status_to_color(ping_status[7]), COLOR_BLACK, start_col + 27, start_row)

def _apply_overall_status(done):
    bads = sum(1 for s in ping_status[:done] if s == NETWORK_BAD)
    if done >= TOTAL_PINGS and bads >= TOTAL_PINGS:
        info_center.internet_status = NETWORK_BAD
    elif bads >= 3:
        info_center.internet_status = NETWORK_PROBLEM
    else:
        info_center.internet_status = NETWORK_GOOD
        
def _ping_one(site):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", site],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5
        )
        return result.returncode == 0
    except Exception:
        return False

def _ping_worker(gen):
    global _ping_done
    sites = info_center.internet_test_sites
    for step in range(TOTAL_PINGS):
        with _ping_lock:
            if gen != _ping_gen:
                return
        site = sites[step // 2]
        success = _ping_one(site)
        with _ping_lock:
            if gen != _ping_gen:
                return
            ping_status[step] = NETWORK_GOOD if success else NETWORK_BAD
            _apply_overall_status(step + 1)
            c = _counts()[site]
            c["total"] += 1
            if not success:
                c["bad"] += 1
        time.sleep(1.5)
    with _ping_lock:
        if gen == _ping_gen:
            _ping_done = True
            st = info_center.internet_status
            if st in (NETWORK_PROBLEM, NETWORK_BAD):
                parts = []
                for site in sites:
                    c = _counts()[site]
                    parts.append("%s %d/%d" % (site, c["bad"], c["total"]))
                bits = []
                for s in ping_status:
                    bits.append(
                        "G" if s == NETWORK_GOOD else
                        "B" if s == NETWORK_BAD else "U"
                    )
                logger.warning(
                    "inet %s pings=%s %s",
                    "BAD" if st == NETWORK_BAD else "YELLOW",
                    "".join(bits),
                    " ".join(parts),
                )
                                
def display_internet_monitor(duration=28.0):
    global _ping_gen, _ping_done, _end_armed

    now = time.monotonic()

    if not info_center.pattern_init:
        info_center.pattern_init = True
        info_center.pattern_end_time = now + duration

        with _ping_lock:
            _ping_gen += 1
            gen = _ping_gen
            _ping_done = False
            _end_armed = False
            for i in range(TOTAL_PINGS):
                ping_status[i] = NETWORK_UNTESTED

        info_center.internet_status = NETWORK_UNTESTED
        clear_lower_panel()
        update_internet_panel()

        threading.Thread(
            target=_ping_worker,
            args=(gen,),
            name="IMonitorPing",
            daemon=True
        ).start()
        return

    update_internet_panel()

    with _ping_lock:
        done = _ping_done
    if done and not _end_armed:
        _end_armed = True
        info_center.pattern_end_time = now + 1.8

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
