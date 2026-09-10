#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.21
# Date:    September 10, 2026
# Module:  CONFIG.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import threading

# Project Imports
from   EEPROM       import eeprom
from   FONT_3X6     import FONT_HEIGHT
from   FONT_3X6     import FONT_WIDTH
from   PLATFORM     import load_platform
from   PLATFORM     import layout as platform_layout
from   PLATFORM     import gpio_pin as platform_gpio

# CONSTANTS

# --- Network / Internet status codes ---
NETWORK_UNTESTED                      =  0
NETWORK_GOOD                          =  1
NETWORK_PROBLEM                       =  2
NETWORK_BAD                           = -1
# --- Power states ---
POWER_ON                              = 0
POWER_BLACKOUT                        = 1
POWER_SLEEP                           = 2
# --- Frame / timing ---
FRAME_INTERVAL                        = 0.025
SCROLL_SPEED_DEFAULT                  = 0.073
DISSOLVE_STEP_DELAY                   = 0.012
DISSOLVE_HOLD_TIME                    = 0.12
DISSOLVE_BATCH_SIZE                   = 6
EXCHANGE_DISSOLVE_BATCH               = 8
# --- Upper panel rotation durations (seconds) ---
UPPER_DURATION_TIME                   = 15.0
UPPER_DURATION_DATE                   = 3.0
UPPER_DURATION_DOW                    = 3.0
UPPER_DURATION_HOLIDAY                = 12.0
# --- Pattern / display timings ---
COLOR_PANEL_SHOW_TIME                 = 1.0
COLOR_PANEL_FINAL_HOLD                = 0.3
PROGRAM_NAME_DURATION                 = 3.0
COPYRIGHT_DURATION                    = 3.0
INTERNET_MONITOR_DURATION             = 28.0
PACMAN_MAX_DURATION                   = 60.0
EXCHANGE_HOLD_TIME                    = 5.0
EXCHANGE_PATTERN_EXTRA                = 10.0
# --- Alert system ---
ALERT_DURATION                        = 300.0
ALERT_FLASH_INTERVAL                  = 1.0
ALERT_SOURCE_LIVE                     = "live"
ALERT_SOURCE_WEB                      = "web_test"
WEB_ALERT_HOLD                        = 600.0
# --- Brightness ---
MIN_BRIGHTNESS                        = 0
MAX_BRIGHTNESS                        = 255
BRIGHTNESS_STEP                       = 8
PANEL_DAYTIME_BRIGHTNESS              = 63
PANEL_NIGHTTIME_BRIGHTNESS            = 31
# --- Data update intervals (seconds) ---
WEATHER_UPDATE_INTERVAL               = 900.0
QUAKE_UPDATE_INTERVAL                 = 300.0
EXCHANGE_UPDATE_INTERVAL              = 900.0
OIL_UPDATE_INTERVAL                   = 900.0
STOCK_UPDATE_INTERVAL                 = 900.0
HOLIDAY_CHECK_INTERVAL                = 3600.0
# --- Earthquake thresholds ---
QUAKE_MIN_MAGNITUDE                   = 5.0
QUAKE_RADIUS_KM                       = 500
QUAKE_ALERT_MAJOR                     = 6.0
QUAKE_ALERT_MINOR                     = 5.0
# --- Exchange rate alert thresholds ---
EXCHANGE_ALERT_MAJOR                  = 0.50
EXCHANGE_ALERT_MINOR                  = 0.25
EXCHANGE_ALERT_MINOR_PCT              = 0.005
EXCHANGE_ALERT_MAJOR_PCT              = 0.010
# --- Weather alert codes ---
WEATHER_HEAVY_CODES                   = {65, 82}
WEATHER_THUNDER_CODES                 = {95, 96, 99}
# --- Pac-Man timings ---
PACMAN_FRAME_DELAY                    = 0.065
PACMAN_PAUSE                          = 0.28
PACMAN_FRIGHT_FLASH                   = 0.35
PACMAN_MOVE_STEP                      = 1
PACMAN_SPACING                        = 10
PACMAN_GHOST_OFFSET                   = 13
# --- Panel geometry defaults ---
DEFAULT_PANEL_WIDTH                   = 32
DEFAULT_PANEL_HEIGHT                  = 16
DEFAULT_PANEL_ORIENTATION             = 180
PANEL_LAYOUT                          = platform_layout()
DEFAULT_GLOBE_LED_COUNT               = 23
# --- Panel layout (rows / columns) ---
UPPER_PANEL_START_ROW                 = 1
UPPER_PANEL_END_ROW                   = 6
LOWER_PANEL_START_ROW                 = 7
LOWER_PANEL_END_ROW                   = 15
LOWER_TEXT_ROW                        = 8
BORDER_INSET                          = 1
# --- Pac-Man ---
PACMAN_Y_OFFSET                       = 7
# --- Internet monitor ---
IMONITOR_TEXT_ROW                     = 8

class UpperPanelState:
    def __init__(self):
        self.initialized              = False
        self.mode                     = 0
        self.pending_mode             = 0
        self.mode_start               = 0.0
        self.dissolve_phase           = 0
        self.dissolve_pixels          = []
        self.dissolve_next            = 0.0
        self.dissolve_batch           = DISSOLVE_BATCH_SIZE
        self.dissolve_hold            = DISSOLVE_HOLD_TIME
        self.durations                = [
            UPPER_DURATION_TIME,
            UPPER_DURATION_DATE,
            UPPER_DURATION_DOW,
            UPPER_DURATION_HOLIDAY
        ]
        self.last_string_draw         = 0.0
        self.holiday_phase            = 0
        self.holiday_pos              = 0
        self.holiday_next             = 0.0
        self.holiday_text             = ""
        self.holiday_buffer           = None
        self._paused                  = False
        self._pause_done              = False

class ScrollState:
    def __init__(self):
        self.phase                    = 0
        self.text                     = ""
        self.pos                      = 0
        self.next                     = 0.0
        self.row                      = 8
        self.speed                    = SCROLL_SPEED_DEFAULT
        self.from_right               = True
        self.fg_list                  = []
        self.bg                       = 0
        self.buffer                   = None
        self.icon                     = None
        self.icon_gap                 = 2
        self.hold_until               = 0.0
        self.center_pos               = 0
        self.text_width               = 0
        self.tight                    = False

class PacmanState:
    def __init__(self):
        self.phase                    = 0
        self.x                        = 0
        self.mouth_open               = True
        self.mouth_counter            = 0
        self.fright_flash             = True
        self.fright_timer             = 0.0
        self.pellets                  = []
        self.next_frame               = 0.0
        self.pause_until              = 0.0

class QuakeDisplayState:
    def __init__(self):
        self.last_built               = 0.0
        self.colors                   = []

class OilDisplayState:
    def __init__(self):
        self.last_built               = 0.0
        self.msg                      = ""
        self.colors                   = []

class StocksDisplayState:
    def __init__(self):
        self.last_built               = 0.0
        self.msg                      = ""
        self.colors                   = []

class WeatherDisplayState:
    def __init__(self):
        self.last_built               = 0.0
        self.msg                      = ""
        self.colors                   = []

class ExchangeDisplayState:
    def __init__(self):
        self.dissolve_phase           = 0
        self.dissolve_pixels          = []
        self.dissolve_next            = 0.0
        self.hold_start               = 0.0
        self.arrow                    = None
        self.last_built               = 0.0
        self.msg                      = ""
        self.colors                   = []

class InternetMonitorState:
    def __init__(self):
        self.step                     = 0
        self.next                     = 0.0

class FetcherState:
    def __init__(self):
        self.started                  = False

class ColorPanelState:
    def __init__(self):
        self.phase                    = 0
        self.next                     = 0.0

class InfoCenterState:
    def __init__(self):
        self.program_name_1_string    = "INFO"
        self.program_name_2_string    = "CENTER"
        self.copyright_string         = "(C)2026"
        self.version_string           = "V1.21"

        self.strip_gpio               = platform_gpio()
        self.panel_layout             = PANEL_LAYOUT
        self.strip_freq               = 800000
        self.strip_dma                = 10
        self.strip_invert             = False
        self.strip_brightness         = 0x1F
        self.strip_channel            = 0

        self.panel_width              = DEFAULT_PANEL_WIDTH
        self.panel_height             = DEFAULT_PANEL_HEIGHT
        self.panel_orientation        = DEFAULT_PANEL_ORIENTATION
        self.panel_led_start          = 0
        self.panel_led_count          = self.panel_width * self.panel_height
        self.panel_led_end            = self.panel_led_start + self.panel_led_count - 1
        self.panel_brightness         = 32

        self.globe_led_count          = DEFAULT_GLOBE_LED_COUNT
        self.globe_led_start          = self.panel_led_count
        self.globe_led_end            = self.globe_led_start + self.globe_led_count - 1
        self.total_led_count          = self.panel_led_count + self.globe_led_count

        self.font_width               = int(FONT_WIDTH)
        self.font_height              = int(FONT_HEIGHT)

        self.day_time                 = True
        self.military_time            = True
        self.temp_celsius             = True
        self.power_flag               = True
        self.debug_mode               = False
        self.auto_brightness          = True
        self.day_brightness           = PANEL_DAYTIME_BRIGHTNESS
        self.night_brightness         = PANEL_NIGHTTIME_BRIGHTNESS
        self.globe_push_enabled       = False

        self.show_pacman              = True
        self.show_weather             = True
        self.show_exchange            = True
        self.show_oil                 = True
        self.show_stocks              = True
        self.show_earthquake          = True

        self.pattern_init             = False
        self.current_pattern          = 0
        self.pattern_end_time         = 0.0

        self.current_time             = "123456"
        self.current_date             = "121425"
        self.current_dow              = "SUN"
        self.saved_time               = "000000"
        self.colon_flag               = True
        self.pm_flag                  = False

        self.is_holiday_today         = False
        self.holiday_name             = ""
        self.holiday_last_check       = 0.0
        self.holiday_check_interval   = HOLIDAY_CHECK_INTERVAL

        self.temp_c                   = 99.9
        self.temp_f                   = 99.9

        self.internet_status          = NETWORK_UNTESTED
        self.internet_test_sites      = [
            "1.1.1.1",
            "8.8.8.8",
            "9.9.9.9",
            "208.67.222.222"
        ]
        self.ping_counts              = {}
        
        self.power_level              = POWER_ON

        self.upper                    = UpperPanelState()
        self.scroll                   = ScrollState()
        self.pacman                   = PacmanState()
        self.quake                    = QuakeDisplayState()
        self.oil                      = OilDisplayState()
        self.stocks                   = StocksDisplayState()
        self.weather                  = WeatherDisplayState()
        self.exchange                 = ExchangeDisplayState()
        self.internet                 = InternetMonitorState()
        self.fetcher                  = FetcherState()
        self.color                    = ColorPanelState()

        self.local_rh                 = None
        self.local_hpa                = None
        self.local_wx_last_update     = 0.0
        
        self.weather_lat              = 15.12736
        self.weather_lon              = 121.00056
        self.weather_location         = "SAN MIGUEL"
        self.weather_temp_c           = 0.0
        self.weather_temp_f           = 0.0
        self.weather_humidity         = 0
        self.weather_code             = 0
        self.weather_description      = "----"
        self.weather_wind_kmh         = 0.0
        self.weather_wind_dir         = 0.0
        self.weather_wind_gusts       = 0.0
        self.weather_wind_compass     = "N"
        self.weather_is_day           = 1
        self.weather_last_update      = 0.0
        self.weather_update_interval  = WEATHER_UPDATE_INTERVAL

        self.quake_min_magnitude      = QUAKE_MIN_MAGNITUDE
        self.quake_radius_km          = QUAKE_RADIUS_KM
        self.quake_update_interval    = QUAKE_UPDATE_INTERVAL
        self.quake_lat                = self.weather_lat
        self.quake_lon                = self.weather_lon
        self.quake_last_update        = 0.0
        self.quake_has_event          = False
        self.quake_magnitude          = 0.0
        self.quake_message            = "RECENT EARTHQUAKE: NONE"

        self.exchange_rate            = 0.0
        self.exchange_last_update     = 0.0
        self.exchange_update_interval = EXCHANGE_UPDATE_INTERVAL
        self.last_exchange_rate       = 0.0
        self.exchange_primary         = "USD"
        self.exchange_secondary       = "PHP"
        self.exchange_base            = "USD"
        self.exchange_quote           = "PHP"
        self.usd_to_primary           = 1.0
        self.usd_to_secondary         = 0.0
        self.pair_rate                = 0.0
        self.primary_valid            = True
        self.secondary_valid          = True

        self.oil_wti                  = 0.0
        self.oil_brent                = 0.0
        self.oil_urals                = 0.0
        self.oil_last_update          = 0.0
        self.oil_update_interval      = OIL_UPDATE_INTERVAL
        self.prev_wti                 = 0.0
        self.prev_brent               = 0.0
        self.prev_urals               = 0.0

        self.stock_symbols            = ["", "", "", "", ""]
        self.stock_prices             = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.stock_prevs              = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.stock_valid              = [False, False, False, False, False]
        self.stock_last_update        = 0.0
        self.stock_update_interval    = STOCK_UPDATE_INTERVAL

        self.alert_level              = 0
        self.alert_until              = 0.0
        self.alert_high_until         = 0.0
        self.alert_low_until          = 0.0
        self.alert_duration           = ALERT_DURATION
        self.alert_source             = ALERT_SOURCE_LIVE
        self.alert_nouns              = []
        self.alert_items              = []
        self.web_alert_weather        = False
        self.web_alert_quake          = False
        self.lock                     = threading.RLock()

        persisted                     = eeprom.load()

        self.auto_brightness          = persisted["auto_brightness"]
        self.military_time            = persisted["military_time"]
        self.panel_brightness         = persisted["brightness"]
        self.temp_celsius             = persisted.get("temp_celsius", True)
        self.day_brightness           = persisted.get("day_brightness", PANEL_DAYTIME_BRIGHTNESS)
        self.night_brightness         = persisted.get("night_brightness", PANEL_NIGHTTIME_BRIGHTNESS)
        self.last_exchange_rate       = persisted["prev_exchange"]
        self.prev_wti                 = persisted["prev_wti"]
        self.prev_brent               = persisted["prev_brent"]
        self.prev_urals               = persisted["prev_urals"]

        self.exchange_primary         = persisted.get("exchange_primary", "USD")
        self.exchange_secondary       = persisted.get("exchange_secondary", "PHP")
        self.exchange_base            = self.exchange_primary
        self.exchange_quote           = self.exchange_secondary
        self.show_pacman              = persisted.get("show_pacman", True)
        self.show_weather             = persisted.get("show_weather", True)
        self.show_exchange            = persisted.get("show_exchange", True)
        self.show_oil                 = persisted.get("show_oil", True)
        self.show_stocks              = persisted.get("show_stocks", True)
        self.show_earthquake          = persisted.get("show_earthquake", True)
        syms = list(persisted.get("stock_symbols", ["", "", "", "", ""]))
        while len(syms) < 5:
            syms.append("")
        self.stock_symbols            = syms[:5]

        _plat, _plat_present          = load_platform()
        if _plat_present:
            self.globe_push_enabled   = _plat["GLOBE_PUSH"] == "1"
        else:
            self.globe_push_enabled   = persisted.get("globe_push_enabled", False)

info_center = InfoCenterState()

HOURS_TENS, HOURS_ONES = 0, 1
MINS_TENS,  MINS_ONES  = 2, 3
SECS_TENS,  SECS_ONES  = 4, 5
MONTH_TENS, MONTH_ONES = 0, 1
DATE_TENS,  DATE_ONES  = 2, 3
YEAR_TENS,  YEAR_ONES  = 4, 5

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
