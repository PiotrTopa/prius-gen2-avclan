#include "led.h"
#include "config.h"
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/sync.h"

static uint32_t s_avc_until;
static bool     s_host;
static uint32_t s_last_update;
static uint32_t s_last_color = 0xFFFFFFFF;

void led_init(void)
{
    gpio_init(PIN_WS2812);
    gpio_set_dir(PIN_WS2812, GPIO_OUT);
    gpio_put(PIN_WS2812, 0);
}

static void put_rgb(uint8_t r, uint8_t g, uint8_t b)
{
    uint32_t grb = ((uint32_t)g << 16) | ((uint32_t)r << 8) | b;
    if (grb == s_last_color) return;

    uint32_t f_sys = clock_get_hz(clk_sys);
    uint32_t t0h = f_sys / 2500000; // ~400ns
    uint32_t t0l = f_sys / 1176470; // ~850ns
    uint32_t t1h = f_sys / 1250000; // ~800ns
    uint32_t t1l = f_sys / 2222222; // ~450ns

    uint32_t save = save_and_disable_interrupts();
    for (int i = 23; i >= 0; i--) {
        if (grb & (1u << i)) {
            gpio_put(PIN_WS2812, 1);
            busy_wait_at_least_cycles(t1h);
            gpio_put(PIN_WS2812, 0);
            busy_wait_at_least_cycles(t1l);
        } else {
            gpio_put(PIN_WS2812, 1);
            busy_wait_at_least_cycles(t0h);
            gpio_put(PIN_WS2812, 0);
            busy_wait_at_least_cycles(t0l);
        }
    }
    restore_interrupts(save);

    s_last_color = grb;
}

void led_flash_avc(void)
{
    s_avc_until = time_us_32() + 40000;   /* 40 ms flash */
}

void led_set_host(bool connected) { s_host = connected; }

void led_task(void)
{
    uint32_t now = time_us_32();
    if ((uint32_t)(now - s_last_update) < 20000) return;   /* 50 Hz max */
    s_last_update = now;

    if ((int32_t)(s_avc_until - now) > 0) { put_rgb(0, 30, 40); return; }   /* cyan */

    /* idle: slow breathing, green when the host has the port open, blue otherwise */
    uint32_t phase = (now / 1000) % 2000;
    uint32_t tri = phase < 1000 ? phase : 2000 - phase;    /* 0..1000 */
    uint8_t lvl = (uint8_t)(2 + tri * 10 / 1000);          /* 2..12 */
    if (s_host)         put_rgb(0, lvl, 0);
    else                put_rgb(0, 0, lvl);
}
