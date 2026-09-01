#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  PACMAN.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

# System Imports
import time

# Project Imports
from   CONFIG         import info_center
from   CONFIG         import PACMAN_FRAME_DELAY
from   CONFIG         import PACMAN_PAUSE
from   CONFIG         import PACMAN_FRIGHT_FLASH
from   CONFIG         import PACMAN_MOVE_STEP
from   CONFIG         import PACMAN_SPACING
from   CONFIG         import PACMAN_GHOST_OFFSET
from   CONFIG         import PACMAN_MAX_DURATION
from   CONFIG         import LOWER_TEXT_ROW
from   CONFIG         import LOWER_PANEL_START_ROW
from   CONFIG         import LOWER_PANEL_END_ROW
from   CONFIG         import PACMAN_Y_OFFSET
from   PANEL          import strip
from   PANEL          import COLOR_BLACK
from   PANEL          import COLOR_RED
from   PANEL          import COLOR_YELLOW
from   PANEL          import COLOR_GREEN
from   PANEL          import COLOR_CYAN
from   PANEL          import COLOR_BLUE
from   PANEL          import COLOR_PURPLE
from   PANEL          import COLOR_WHITE
from   PANEL          import COLOR_PINK
from   PANEL          import COLOR_ORANGE
from   PANEL          import COLOR_BLUE_FRIGHTENED
from   PANEL          import get_conversion_value
from   PANEL          import apply_brightness
from   PANEL          import clear_lower_panel
from   PANEL          import set_pixel

# Sprites
PACMAN_OPEN_RIGHT = [
    0b00111100, 0b01111110, 0b11111111, 0b11111111,
    0b11100111, 0b11000011, 0b01000010, 0b00000000
]
PACMAN_CLOSED_RIGHT = [
    0b00111100, 0b01111110, 0b11111111, 0b11111111,
    0b11111111, 0b11111111, 0b01111110, 0b00111100
]
PACMAN_OPEN_LEFT = [
    0b00000000, 0b01000010, 0b11000011, 0b11100111,
    0b11111111, 0b11111111, 0b01111110, 0b00111100
]
PACMAN_CLOSED_LEFT = [
    0b00111100, 0b01111110, 0b11111111, 0b11111111,
    0b11111111, 0b11111111, 0b01111110, 0b00111100
]
GHOST_BODY_RIGHT = [
    0b11111100, 0b11111110, 0b01111111, 0b11111111,
    0b01111111, 0b11111111, 0b01111110, 0b11111100
]
GHOST_BODY_LEFT = [
    0b11111100, 0b01111110, 0b11111111, 0b01111111,
    0b11111111, 0b01111111, 0b11111110, 0b11111100
]

X_MIN    = 1

def draw_sprite(bitmap, start_col, color, facing_right=True, is_pacman=False, y_offset=PACMAN_Y_OFFSET):
    if strip is None or not info_center.power_flag:
        return

    x_max = info_center.panel_width - 2

    for col_offset, bits in enumerate(bitmap):
        col = start_col + col_offset
        if not (X_MIN <= col <= x_max):
            continue
        for row in range(8):
            if (bits >> row) & 1:
                r = row + y_offset
                if 7 <= r <= 14:
                    i = get_conversion_value(row=r, column=col)
                    if info_center.panel_led_start <= i <= info_center.panel_led_end:
                        set_pixel(i, apply_brightness(color, info_center.panel_brightness))

    if is_pacman:
        eye_pos   = [(2, 3)] if facing_right else [(2, 4)]
        pupil_pos = eye_pos
        pupil_color = COLOR_BLACK
        draw_white_eyes = False
    else:
        if facing_right:
            eye_pos   = [(2,2),(2,3),(3,2),(3,3), (2,5),(2,6),(3,5),(3,6)]
            pupil_pos = [(3,3), (3,6)]
        else:
            eye_pos   = [(2,1),(2,2),(3,1),(3,2), (2,4),(2,5),(3,4),(3,5)]
            pupil_pos = [(3,1), (3,4)]
        pupil_color = COLOR_BLUE
        draw_white_eyes = True

    if draw_white_eyes:
        for r, c in eye_pos:
            col = start_col + c
            rr  = r + y_offset
            if X_MIN <= col <= x_max and 7 <= rr <= 14:
                i = get_conversion_value(row=rr, column=col)
                if info_center.panel_led_start <= i <= info_center.panel_led_end:
                    set_pixel(i, apply_brightness(COLOR_WHITE, info_center.panel_brightness))

    for r, c in pupil_pos:
        col = start_col + c
        rr  = r + y_offset
        if X_MIN <= col <= x_max and 7 <= rr <= 14:
            i = get_conversion_value(row=rr, column=col)
            if info_center.panel_led_start <= i <= info_center.panel_led_end:
                set_pixel(i, apply_brightness(pupil_color, info_center.panel_brightness))

def display_pacman():
    if strip is None or not info_center.power_flag:
        info_center.pattern_end_time = time.monotonic()
        return

    now = time.monotonic()
    pac = info_center.pacman

    x_max                 = info_center.panel_width - 2
    frame_delay           = PACMAN_FRAME_DELAY
    pause                 = PACMAN_PAUSE
    fright_flash_interval = PACMAN_FRIGHT_FLASH
    y_offset              = PACMAN_Y_OFFSET
    x_min                 = 1
    spacing               = PACMAN_SPACING
    ghost_offset          = PACMAN_GHOST_OFFSET
    exit_right            = x_max + ghost_offset + 3 * spacing + 8
    exit_left             = -14
    pellet_row            = 4 + y_offset
    pellet_spacing        = 7
    move_step             = PACMAN_MOVE_STEP

    if not info_center.pattern_init:
        info_center.pattern_init = True
        pac.phase        = 0
        pac.x            = -14
        pac.mouth_open   = True
        pac.mouth_counter = 0
        pac.fright_flash = True
        pac.fright_timer = now
        pac.next_frame   = now
        pac.pause_until  = now + pause

        min_margin = 3
        max_num    = ((x_max - x_min - 2 * min_margin) // pellet_spacing) + 1
        total_span = (max_num - 1) * pellet_spacing
        start      = x_min + ((x_max - x_min) - total_span) // 2
        pac.pellets = list(range(start, start + total_span + 1, pellet_spacing))

        info_center.pattern_end_time = now + PACMAN_MAX_DURATION

        clear_lower_panel()
        for px in pac.pellets:
            if x_min <= px <= x_max:
                i = get_conversion_value(row=pellet_row, column=px)
                if info_center.panel_led_start <= i <= info_center.panel_led_end:
                    set_pixel(i, apply_brightness(COLOR_WHITE, info_center.panel_brightness))
        return

    if pac.phase < 4:
        info_center.pattern_end_time = now + 5.0

    if pac.phase == 0:
        if now >= pac.pause_until:
            pac.phase = 1
            pac.next_frame = now

    elif pac.phase == 1:
        if now >= pac.next_frame:
            pac.x += move_step
            pac.mouth_counter += 1
            if pac.mouth_counter >= 3:
                pac.mouth_open = not pac.mouth_open
                pac.mouth_counter = 0

            pac.pellets = [p for p in pac.pellets
                           if not (pac.x <= p <= pac.x + 7)]

            clear_lower_panel()
            for px in pac.pellets:
                if x_min <= px <= x_max:
                    i = get_conversion_value(row=pellet_row, column=px)
                    if info_center.panel_led_start <= i <= info_center.panel_led_end:
                        set_pixel(i, apply_brightness(COLOR_WHITE, info_center.panel_brightness))

            for i, gcolor in enumerate([COLOR_RED, COLOR_PINK, COLOR_CYAN, COLOR_ORANGE]):
                gx = pac.x - ghost_offset - (i * spacing)
                draw_sprite(GHOST_BODY_RIGHT, gx, gcolor, facing_right=True)

            pac_bmp = PACMAN_OPEN_RIGHT if pac.mouth_open else PACMAN_CLOSED_RIGHT
            draw_sprite(pac_bmp, pac.x, COLOR_YELLOW, facing_right=True, is_pacman=True)

            pac.next_frame = now + frame_delay

            if pac.x > exit_right:
                pac.phase = 2
                pac.pause_until = now + pause
                clear_lower_panel()

    elif pac.phase == 2:
        if now >= pac.pause_until:
            pac.phase = 3
            pac.x = exit_right
            pac.mouth_open = True
            pac.mouth_counter = 0
            pac.fright_flash = True
            pac.fright_timer = now
            pac.next_frame = now

    elif pac.phase == 3:
        if now >= pac.next_frame:
            pac.x -= move_step
            pac.mouth_counter += 1
            if pac.mouth_counter >= 3:
                pac.mouth_open = not pac.mouth_open
                pac.mouth_counter = 0

            if now - pac.fright_timer >= fright_flash_interval:
                pac.fright_flash = not pac.fright_flash
                pac.fright_timer = now

            clear_lower_panel()

            ghost_colors = ([COLOR_BLUE_FRIGHTENED]*4 if pac.fright_flash
                            else [COLOR_WHITE]*4)
            for i, gcolor in enumerate(ghost_colors):
                gx = pac.x - ghost_offset - (i * spacing)
                draw_sprite(GHOST_BODY_LEFT, gx, gcolor, facing_right=False)

            pac_bmp = PACMAN_OPEN_LEFT if pac.mouth_open else PACMAN_CLOSED_LEFT
            draw_sprite(pac_bmp, pac.x, COLOR_YELLOW, facing_right=False, is_pacman=True)

            pac.next_frame = now + frame_delay

            if pac.x < exit_left:
                pac.phase = 4
                clear_lower_panel()
                info_center.pattern_end_time = now + 0.3

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
