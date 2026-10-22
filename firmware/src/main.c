/*
 * AVC-LAN (Toyota IEBus) transceiver — RP2040 / RP2350, pico-sdk.
 *
 * One core, one non-blocking loop. The bus is serviced by hardware (PIO +
 * IRQ for RX, PIO + DMA for TX), so nothing here ever waits: a frame goes
 * PIO -> IRQ decoder -> ring -> USB within the loop iteration in which its
 * last bit ended.
 */
#include "config.h"
#include "out.h"
#include "usb_cdc.h"
#include "avclan.h"
#include "commands.h"
#include "led.h"

#include "pico/stdlib.h"
#include "hardware/watchdog.h"

int main(void)
{
    /* No stdio: the USB CDC port belongs to the NDJSON protocol. */
    led_init();
    usb_cdc_init(commands_handle_line);
    avclan_init();

    watchdog_enable(WATCHDOG_MS, true);

    /* Give the host a moment to see the port before the banner. */
    uint32_t t0 = now_ms();
    while (now_ms() - t0 < 300) { usb_cdc_task(); watchdog_update(); }
    sys_emit_ready();

    uint32_t last_hb = now_ms();
    bool host_was = false;

    for (;;) {
        watchdog_update();

        avclan_task();          /* 1. decoded AVC-LAN frames out, auto-replies, TX kick */
        usb_cdc_task();         /* 2. USB device task + host commands */

        uint32_t now = now_ms();
        if (now - last_hb >= HEARTBEAT_MS) {
            last_hb = now;
            sys_emit_heartbeat();
        }

        bool host = usb_cdc_host_connected();
        if (host != host_was) { host_was = host; led_set_host(host); }
        /* The WS2812 bit-bang masks interrupts for ~30 us; never do it while
         * a frame is on the bus, where it could delay an ACK-slot stretch. */
        if (!avclan_bus_busy()) led_task();
    }
}
