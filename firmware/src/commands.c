/* Host command dispatch (NDJSON lines from USB) and the system messages. */
#include "commands.h"
#include "config.h"
#include "out.h"
#include "json_util.h"
#include "avclan.h"
#include "usb_cdc.h"

#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "hardware/watchdog.h"
#include <string.h>
#include <stdio.h>

bool g_log_rx = false;

static uint32_t s_boot_ms;
static uint8_t  s_hb_counter;

#define MAX_TOKENS 200

/* ------------------------------------------------------------------------ */
/* id 0: system                                                              */
/* ------------------------------------------------------------------------ */

static void handle_sys(const json_t *j, int d)
{
    int t;
    bool b;

    if ((t = json_obj_get(j, d, "seq")) >= 0 && json_get_bool(j, t, &b)) {
        g_out.seq_enabled = b;
        out_json("{\"id\":0,\"d\":{\"msg\":\"CFG_UPDATED\",\"seq\":%s}}", b ? "true" : "false");
    }
    if ((t = json_obj_get(j, d, "test")) >= 0) {
        if (json_str_eq(j, t, "avc")) {
            bool rx_idle, rx_drive, rx_after;
            avclan_test_loopback(&rx_idle, &rx_drive, &rx_after);
            out_json("{\"id\":0,\"d\":{\"test\":\"avc\",\"rx_idle\":%d,\"rx_drive\":%d,\"rx_after\":%d}}",
                     rx_idle ? 1 : 0, rx_drive ? 1 : 0, rx_after ? 1 : 0);
        } else if (json_str_eq(j, t, "tx_high")) {
            avclan_test_tx(true);
            out_json("{\"id\":0,\"d\":{\"test\":\"tx_high\",\"gp1\":1,\"gp0\":%d}}", avclan_rx_level() ? 1 : 0);
        } else if (json_str_eq(j, t, "tx_low")) {
            avclan_test_tx(false);
            out_json("{\"id\":0,\"d\":{\"test\":\"tx_low\",\"gp1\":0,\"gp0\":%d}}", avclan_rx_level() ? 1 : 0);
        }
    }

    int a = json_obj_get(j, d, "a");
    if (a < 0) return;

    if (json_str_eq(j, a, "whoami") || json_str_eq(j, a, "identify") || json_str_eq(j, a, "id")) {
        sys_emit_ident();
    } else if (json_str_eq(j, a, "stats")) {
        sys_emit_stats();
    } else if (json_str_eq(j, a, "avc_raw")) {
        bool on = true;
        json_get_bool(j, json_obj_get(j, d, "on"), &on);
        avclan_set_raw(on);
        out_json("{\"id\":0,\"d\":{\"msg\":\"CFG_UPDATED\",\"avc_raw\":%s}}", on ? "true" : "false");
    } else if (json_str_eq(j, a, "avc_err")) {
        bool on = true;
        json_get_bool(j, json_obj_get(j, d, "on"), &on);
        g_avc.debug_errors = on;
        out_json("{\"id\":0,\"d\":{\"msg\":\"CFG_UPDATED\",\"avc_err\":%s}}", on ? "true" : "false");
    } else if (json_str_eq(j, a, "avc_cfg")) {
        long v;
        int pol = json_obj_get(j, d, "pol");
        if ((t = json_obj_get(j, d, "ack")) >= 0) {
            uint32_t a = 0;
            if (json_get_hexint(j, t, &a) && a <= 0xFFF) avclan_set_ack_addr((uint16_t)a);
            else avclan_set_ack_addr(0);
        }
        if ((t = json_obj_get(j, d, "glitch")) >= 0 && json_get_long(j, t, &v) && v > 0 && v < 100) g_avc_thr.glitch_us = (uint16_t)v;
        if ((t = json_obj_get(j, d, "t1")) >= 0 && json_get_long(j, t, &v) && v > 0 && v < 200)     g_avc_thr.one_max_us = (uint16_t)v;
        if ((t = json_obj_get(j, d, "t0")) >= 0 && json_get_long(j, t, &v) && v > 0 && v < 1000)    g_avc_thr.zero_max_us = (uint16_t)v;
        if ((t = json_obj_get(j, d, "tstart")) >= 0 && json_get_long(j, t, &v) && v > 0 && v < 5000) g_avc_thr.start_max_us = (uint16_t)v;
        if (pol >= 0) {
            if (json_str_eq(j, pol, "auto"))     avclan_set_polarity(AVC_POL_AUTO);
            else if (json_str_eq(j, pol, "hi"))  avclan_set_polarity(AVC_POL_DOMINANT_HIGH);
            else if (json_str_eq(j, pol, "lo"))  avclan_set_polarity(AVC_POL_DOMINANT_LOW);
        }
        out_json("{\"id\":0,\"d\":{\"msg\":\"CFG_UPDATED\",\"avc_cfg\":{\"pol\":\"%s\",\"glitch\":%u,\"t1\":%u,\"t0\":%u,\"tstart\":%u,\"ack\":\"%03X\"}}}",
                 g_avc.dominant_low ? "lo" : "hi", g_avc_thr.glitch_us, g_avc_thr.one_max_us,
                 g_avc_thr.zero_max_us, g_avc_thr.start_max_us, g_avc.ack_addr);
    } else if (json_str_eq(j, a, "log_rx")) {
        bool on = true;
        json_get_bool(j, json_obj_get(j, d, "on"), &on);
        g_log_rx = on;
        out_json("{\"id\":0,\"d\":{\"msg\":\"CFG_UPDATED\",\"log_rx\":%s}}", on ? "true" : "false");
    } else if (json_str_eq(j, a, "reset")) {
        out_json("{\"id\":0,\"d\":{\"msg\":\"RESET\"}}");
        sleep_ms(20);
        watchdog_reboot(0, 0, 10);
        for (;;) tight_loop_contents();
    } else if (json_str_eq(j, a, "bootsel")) {
        out_json("{\"id\":0,\"d\":{\"msg\":\"BOOTSEL\"}}");
        sleep_ms(50);
        reset_usb_boot(0, 0);
    }
}

/* ------------------------------------------------------------------------ */
/* id 2: AVC-LAN transmit                                                    */
/* ------------------------------------------------------------------------ */

static bool parse_avc_frame(const json_t *j, int d, avc_frame_t *f)
{
    memset(f, 0, sizeof(*f));
    uint32_t m, s, c;
    if (!json_get_hexint(j, json_obj_get(j, d, "m"), &m) || m > 0xFFF ||
        !json_get_hexint(j, json_obj_get(j, d, "s"), &s) || s > 0xFFF ||
        !json_get_int_base(j, json_obj_get(j, d, "c"), 10, &c) || c > 0xF) {
        out_sys_err("BAD_AVC_HEADER");
        return false;
    }
    f->master = (uint16_t)m;
    f->slave = (uint16_t)s;
    f->control = (uint8_t)c;

    int arr = json_obj_get(j, d, "d");
    int n = json_count(j, arr);
    if (arr < 0 || n > AVC_MAX_DATA) { out_sys_err("BAD_AVC_DATA"); return false; }
    for (int i = 0; i < n; i++) {
        uint32_t v;
        if (!json_get_hexint(j, json_array_item(j, arr, i), &v) || v > 255) { out_sys_err("BAD_AVC_DATA"); return false; }
        f->data[i] = (uint8_t)v;
    }
    f->len = (uint8_t)n;

    bool b = (s == 0xFFF);
    json_get_bool(j, json_obj_get(j, d, "b"), &b);
    f->broadcast = b;
    return true;
}

/* {"id":2,"d":{"a":"auto","slot":0,"on":true,"m":"110","s":"FFF","d":["12","01","00"],
 *               "tx":{"m":"178","s":"110","c":15,"d":[...]}}}   set a slot
 * {"id":2,"d":{"a":"auto","slot":0,"on":false}}                 clear a slot
 * {"id":2,"d":{"a":"auto"}}                                     report the table */
static void handle_avc_auto(const json_t *j, int d)
{
    long slot = -1;
    json_get_long(j, json_obj_get(j, d, "slot"), &slot);
    bool on = true;
    json_get_bool(j, json_obj_get(j, d, "on"), &on);

    if (slot < 0) {
        char buf[512]; char *p = buf;
        p += sprintf(p, "{\"id\":2,\"d\":{\"auto\":[");
        for (int i = 0; i < AVC_AUTO_SLOTS; i++) {
            const avc_auto_t *a = avclan_auto_get(i);
            p += sprintf(p, "%s{\"slot\":%d,\"on\":%s,\"hits\":%lu}", i ? "," : "", i,
                         a->on ? "true" : "false", (unsigned long)a->hits);
        }
        p += sprintf(p, "]}}");
        out_line(buf, (size_t)(p - buf));
        return;
    }
    if (slot >= AVC_AUTO_SLOTS) { out_sys_err("BAD_AUTO_SLOT"); return; }
    if (!on) {
        avclan_auto_set((int)slot, NULL);
        out_json("{\"id\":2,\"d\":{\"auto\":%ld,\"on\":false}}", slot);
        return;
    }
    avc_auto_t a;
    memset(&a, 0, sizeof(a));
    a.on = true;
    uint32_t v;
    int t;
    a.master = 0xFFFF; a.slave = 0xFFFF;
    if ((t = json_obj_get(j, d, "m")) >= 0) { if (!json_get_hexint(j, t, &v) || v > 0xFFF) { out_sys_err("BAD_AVC_HEADER"); return; } a.master = (uint16_t)v; }
    if ((t = json_obj_get(j, d, "s")) >= 0) { if (!json_get_hexint(j, t, &v) || v > 0xFFF) { out_sys_err("BAD_AVC_HEADER"); return; } a.slave = (uint16_t)v; }
    int arr = json_obj_get(j, d, "d");
    int n = arr >= 0 ? json_count(j, arr) : 0;
    if (n > AVC_AUTO_PREFIX) { out_sys_err("BAD_AVC_DATA"); return; }
    for (int i = 0; i < n; i++) {
        if (!json_get_hexint(j, json_array_item(j, arr, i), &v) || v > 255) { out_sys_err("BAD_AVC_DATA"); return; }
        a.prefix[i] = (uint8_t)v;
    }
    a.plen = (uint8_t)n;
    int tx = json_obj_get(j, d, "tx");
    if (tx < 0 || !parse_avc_frame(j, tx, &a.reply)) return;
    if (!avclan_auto_set((int)slot, &a)) { out_sys_err("BAD_AVC_DATA"); return; }
    out_json("{\"id\":2,\"d\":{\"auto\":%ld,\"on\":true}}", slot);
}

static void handle_avc(const json_t *j, int d)
{
    int a = json_obj_get(j, d, "a");
    if (a >= 0 && json_str_eq(j, a, "auto")) { handle_avc_auto(j, d); return; }
    avc_frame_t f;
    if (!parse_avc_frame(j, d, &f)) return;
    if (!avclan_send(&f)) out_sys_err("AVC_TX_QUEUE_FULL");
}

/* ------------------------------------------------------------------------ */

void commands_handle_line(char *line, size_t len)
{
    long id;
    if (!json_scan_id(line, len, &id)) { out_json("{\"id\":0,\"d\":{\"err\":\"CMD_ERR\",\"msg\":\"no id\"}}"); return; }

    static jsmntok_t toks[MAX_TOKENS];
    json_t j;
    int n = json_parse(&j, line, len, toks, MAX_TOKENS);
    if (n < 0) { out_json("{\"id\":0,\"d\":{\"err\":\"JSON_PARSE\",\"code\":%d}}", n); return; }
    int d = json_obj_get(&j, 0, "d");
    if (d < 0) return;

    if (g_log_rx) {
        char a[24] = "";
        json_str_copy(&j, json_obj_get(&j, d, "a"), a, sizeof(a));
        out_json("{\"id\":0,\"d\":{\"log\":\"USB_RX\",\"dev\":%ld,\"a\":\"%s\"}}", id, a);
    }

    switch (id) {
    case DEV_SYS: handle_sys(&j, d); break;
    case DEV_AVC: handle_avc(&j, d); break;
    default:      out_sys_err("UNKNOWN_DEVICE"); break;
    }
}

/* ------------------------------------------------------------------------ */
/* system messages                                                           */
/* ------------------------------------------------------------------------ */

void sys_emit_ready(void)
{
    s_boot_ms = now_ms();
    out_json("{\"id\":0,\"d\":{\"msg\":\"GATEWAY_READY\",\"ver\":\"" FW_VERSION "\",\"role\":\"" FW_ROLE "\","
             "\"cores\":1,\"fw\":\"c-sdk\",\"board\":\"" PICO_BOARD "\",\"avc_pol\":\"%s\"}}",
             g_avc.dominant_low ? "lo" : "hi");
}

void sys_emit_ident(void)
{
    out_json("{\"id\":0,\"d\":{\"msg\":\"IDENT\",\"role\":\"" FW_ROLE "\",\"ver\":\"" FW_VERSION "\"}}");
}

void sys_emit_heartbeat(void)
{
    s_hb_counter++;
    uint32_t up = (now_ms() - s_boot_ms) / 1000;
    out_json("{\"id\":0,\"d\":{\"msg\":\"GW_HB\",\"role\":\"" FW_ROLE "\",\"ver\":\"" FW_VERSION "\",\"n\":%u,\"up\":%lu,"
             "\"avc\":%lu,\"avc_err\":%lu,\"avc_lvl\":%d,\"drop\":%lu}}",
             s_hb_counter, (unsigned long)up,
             (unsigned long)g_avc.frames_out,
             (unsigned long)(g_avc_rx.parity_errors + g_avc_rx.length_errors + g_avc.timeouts),
             avclan_rx_level() ? 1 : 0, (unsigned long)g_out.dropped);
}

void sys_emit_stats(void)
{
    out_json("{\"id\":0,\"d\":{\"stats\":{"
             "\"avc\":{\"frames\":%lu,\"echo\":%lu,\"parity\":%lu,\"length\":%lu,\"aborted\":%lu,\"timeouts\":%lu,"
             "\"stray\":%lu,\"glitch\":%lu,\"ring_ovf\":%lu,\"words\":%lu,\"tx\":%lu,\"tx_deferred\":%lu,\"tx_qfull\":%lu,\"tx_auto\":%lu,\"acks\":%lu,\"ack\":\"%03X\",\"pol\":\"%s\"},"
             "\"usb\":{\"lines\":%lu,\"dropped\":%lu,\"rx_lines\":%lu,\"rx_overlong\":%lu,\"connected\":%d}}}}",
             (unsigned long)g_avc.frames_out, (unsigned long)g_avc.frames_echo,
             (unsigned long)g_avc_rx.parity_errors, (unsigned long)g_avc_rx.length_errors,
             (unsigned long)g_avc_rx.aborted, (unsigned long)g_avc.timeouts,
             (unsigned long)g_avc_rx.stray_bits, (unsigned long)g_avc_rx.glitches,
             (unsigned long)g_avc.ring_overflow, (unsigned long)g_avc.fifo_words,
             (unsigned long)g_avc.tx_frames, (unsigned long)g_avc.tx_deferred, (unsigned long)g_avc.tx_queue_full, (unsigned long)g_avc.tx_auto, (unsigned long)g_avc.acks, g_avc.ack_addr,
             g_avc.dominant_low ? "lo" : "hi",
             (unsigned long)g_out.lines, (unsigned long)g_out.dropped, (unsigned long)g_usb.rx_lines,
             (unsigned long)g_usb.rx_overlong, usb_cdc_host_connected() ? 1 : 0);
}
