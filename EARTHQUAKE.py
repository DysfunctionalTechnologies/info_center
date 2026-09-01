#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  EARTHQUAKE.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import logging
import time

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import LOWER_TEXT_ROW
from   CONFIG         import LOWER_PANEL_START_ROW
from   CONFIG         import LOWER_PANEL_END_ROW
from   DATA_FETCHER   import is_data_fresh
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_WHITE
from   PANEL          import clear_lower_panel
from   PANEL          import continuous_scroll_message

logger = logging.getLogger(__name__)

def display_earthquake():
    now = time.monotonic()
    quake = info_center.quake

    fresh = is_data_fresh(info_center.quake_last_update, 600.0)

    need_rebuild = (
        not info_center.pattern_init or
        info_center.quake_last_update > quake.last_built or
        not fresh
    )

    if need_rebuild:
        info_center.pattern_init = True
        clear_lower_panel()

        if not fresh:
            msg = "QUAKE OFFLINE"
            colors = [COLOR_WHITE] * len(msg)
        else:
            msg = info_center.quake_message
            if info_center.quake_has_event and info_center.alert_level == 2:
                colors = [COLOR_RED] * len(msg)
            elif info_center.quake_has_event and info_center.alert_level == 1:
                colors = [COLOR_YELLOW] * len(msg)
            elif info_center.quake_has_event and info_center.quake_magnitude >= 5.0:
                colors = [COLOR_CYAN] * len(msg)
            else:
                colors = [COLOR_WHITE] * len(msg)

        quake.colors     = colors
        quake.last_built = info_center.quake_last_update

        continuous_scroll_message(
            string_to_scroll=msg,
            from_right=True,
            row=LOWER_TEXT_ROW,
            char_colors=colors
        )
        return

    continuous_scroll_message(
        string_to_scroll=info_center.quake_message if fresh else "QUAKE OFFLINE",
        from_right=True,
        row=LOWER_TEXT_ROW,
        char_colors=quake.colors or [COLOR_WHITE] * 20
    )

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
