#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.20
# Date:    September 5, 2026
# Module:  TEMPERATURE.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import glob
import logging
import os
import time

# Logging
logger = logging.getLogger(__name__)

# Constants
BASE_DIR             = '/sys/bus/w1/devices/'
SENSOR_PATTERN       = '28*'
MAX_RETRIES          = 5
RETRY_DELAY          = 0.2
DEFAULT_TEMP_C       = -99.0
DEFAULT_TEMP_F       = -99.0
CALIBRATION_OFFSET_C = 0.0
CACHE_SECONDS        = 45.0          # how long to reuse a reading

# Global variables
last_temp_c          = DEFAULT_TEMP_C
last_temp_f          = DEFAULT_TEMP_F
last_read_time       = 0.0

def find_sensor():
    try:
        device_folders = glob.glob(os.path.join(BASE_DIR, SENSOR_PATTERN))
        if not device_folders:
            raise FileNotFoundError("No DS18B20 sensor found")
        return os.path.join(device_folders[0], 'w1_slave')
    except Exception as e:
        logger.error(f"Error finding sensor: {e}")
        return None

def read_temp_raw(device_file):
    try:
        with open(device_file, 'r') as f:
            return f.readlines()
    except (FileNotFoundError, IOError) as e:
        logger.error(f"Error reading sensor file {device_file}: {e}")
        return None

def read_temp():
    global last_temp_c, last_temp_f, last_read_time

    now = time.monotonic()

    # Return cached value if it is still fresh
    if (last_read_time > 0.0 and
        (now - last_read_time) < CACHE_SECONDS and
        last_temp_c > -90.0):          # -99 is the “invalid” sentinel
        return last_temp_c, last_temp_f

    device_file = find_sensor()
    if not device_file:
        logger.warning("Using last known temperature due to sensor detection failure")
        return last_temp_c, last_temp_f

    retries = 0
    while retries < MAX_RETRIES:
        lines = read_temp_raw(device_file)
        if lines is None or len(lines) < 2:
            retries += 1
            time.sleep(RETRY_DELAY)
            continue
        
        if lines[0].strip()[-3:] == 'YES':
            try:
                temp_string = lines[1].split('t=')[1].strip()
                temp_c = float(temp_string) / 1000.0 + CALIBRATION_OFFSET_C
                temp_f = (temp_c * 9/5) + 32
                last_temp_c = temp_c
                last_temp_f = temp_f
                last_read_time = now
                return temp_c, temp_f
            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing temperature data: {e}")
                break
        
        retries += 1
        time.sleep(RETRY_DELAY)
    
    logger.warning(f"Temperature read failed after {MAX_RETRIES} retries, using last known values")
    return last_temp_c, last_temp_f

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
