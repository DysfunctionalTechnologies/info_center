#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "piolib.h"
#include "hardware/pio.h"
#include "ws2812.pio.h"

static PIO pio;
static int sm;
static int nleds;
static uint32_t *buf;

int ws_init(int gpio, int count)
{
    pio_init();
    pio = pio_open(0);
    if (PIO_IS_ERR(pio) || count <= 0)
        return -1;

    sm = pio_claim_unused_sm(pio, true);
    if (sm < 0)
        return -2;

    if (pio_sm_config_xfer(pio, sm, PIO_DIR_TO_SM, 4096, 2) != 0)
        return -3;

    uint offset = pio_add_program(pio, &ws2812_program);
    ws2812_program_init(pio, sm, offset, (uint)gpio, 800000.0f, false);

    nleds = count;
    buf = calloc((size_t)count, sizeof(uint32_t));
    return buf ? 0 : -4;
}

void ws_set(int index, uint32_t rgb)
{
    if (!buf || index < 0 || index >= nleds)
        return;
    uint8_t r = (rgb >> 16) & 0xFF;
    uint8_t g = (rgb >>  8) & 0xFF;
    uint8_t b =  rgb        & 0xFF;
    buf[index] = (((uint32_t)g << 16) | ((uint32_t)r << 8) | b) << 8;
}

int ws_show(void)
{
    if (!buf)
        return -1;
    return pio_sm_xfer_data(pio, sm, PIO_DIR_TO_SM,
                            (uint)nleds * 4, buf);
}

void ws_close(void)
{
    if (buf && pio && !PIO_IS_ERR(pio)) {
        memset(buf, 0, (size_t)nleds * 4);
        pio_sm_xfer_data(pio, sm, PIO_DIR_TO_SM, (uint)nleds * 4, buf);
    }
    free(buf);
    buf = NULL;
    if (pio && !PIO_IS_ERR(pio))
        pio_close(pio);
    pio = NULL;
}
