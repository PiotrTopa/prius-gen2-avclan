/* On-board WS2812 status LED (bit-banged, no PIO). */
#pragma once
#include <stdbool.h>

void led_init(void);
void led_flash_avc(void);            /* 40 ms cyan flash: AVC-LAN frame delivered */
void led_set_host(bool connected);
void led_task(void);
