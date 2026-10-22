/* Build-time configuration: pins, protocol constants, timing. */
#pragma once

/* Carved out of a multi-bus (AVC-LAN / CAN / RS485) gateway firmware; this
 * build keeps only the AVC-LAN transceiver. The version follows that firmware. */
#define FW_VERSION      "3.2.0"
#define FW_ROLE         "avclan"

#ifndef PICO_BOARD
#define PICO_BOARD      "unknown"
#endif

/* ---- Pin map ------------------------------------------------------------ */
#define PIN_AVC_RX      0    /* comparator output (e.g. LM339, open collector + 4k7 to 3V3) */
#define PIN_AVC_TX      1    /* -> 2k2 -> NPN (e.g. BC547) base; HIGH = drive dominant */

#ifdef PICO_DEFAULT_WS2812_PIN
#define PIN_WS2812      PICO_DEFAULT_WS2812_PIN
#else
#define PIN_WS2812      16
#endif

#define USB_MAX_LINE    4096 /* longest accepted host command line (bytes) */

/* ---- NDJSON device ids -------------------------------------------------- */
#define DEV_SYS         0
#define DEV_AVC         2    /* 2 kept from the gateway protocol (1 was CAN) */

/* ---- Timing ------------------------------------------------------------- */
#define HEARTBEAT_MS        1000
#define WATCHDOG_MS         8000

/* AVC-LAN: a frame with no dominant pulse for this long is abandoned. */
#define AVC_FRAME_TIMEOUT_US  600
/* AVC-LAN: bus must be free of pulses for this long before we transmit. */
#define AVC_TX_IDLE_US        250
