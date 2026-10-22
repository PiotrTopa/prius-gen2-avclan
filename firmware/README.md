# AVC-LAN transceiver firmware (RP2040 / RP2350)

Firmware for a Waveshare **RP2040-Zero** (or the pin-compatible **RP2350-Zero**)
that turns it into a USB AVC-LAN (Toyota's IEBus variant) transceiver:

* every frame on the bus is decoded in hardware time and sent to the host as one
  JSON line the moment its last ACK slot ends (no bus-silence timeout, no batching);
* the host can transmit frames, and the firmware can **acknowledge** frames for
  one emulated address and **auto-reply** to up to four frame patterns by itself,
  which is what an ECU emulator needs (see [Emulating an ECU](#emulating-an-ecu-ack-stretch-and-auto-reply)).

Version **3.2.0**. This firmware was carved out of a multi-bus (AVC-LAN / CAN / RS485)
gateway firmware; only the AVC-LAN part is kept, and its wire protocol is unchanged,
so the version number follows that firmware.

```
firmware/
├── CMakeLists.txt, build.sh, pico_sdk_import.cmake   build (pico-sdk 2.x, Ninja)
├── src/
│   ├── avclan.pio            RX pulse-width capture, TX bit generator (PIO)
│   ├── avclan_codec.[ch]     IEBus bit-stream decoder/encoder (pure C, host-testable)
│   ├── avclan.[ch]           PIO/IRQ/DMA glue, polarity, ACK stretch, auto-reply, echo tagging
│   ├── commands.[ch]         NDJSON command dispatch, heartbeat, stats
│   ├── out.[ch]              line output, seq counter
│   ├── usb_cdc.[ch], usb_descriptors.c, tusb_config.h   TinyUSB CDC-ACM
│   ├── led.[ch]              on-board WS2812 status LED (bit-banged)
│   ├── json_util.[ch]        small helpers over jsmn
│   └── jsmn.h, jsmn_LICENSE  jsmn JSON tokenizer (MIT, Serge A. Zaitsev)
└── test/
    ├── run.sh, test_codec.c  host unit tests (codec round trips, JSON helpers)
    └── pio_sim.py            cycle-level simulation of both PIO programs (needs a build)
```

## Hardware

| Function | GPIO | Notes |
|---|---|---|
| AVC-LAN RX | **GP0** | comparator output (e.g. LM339, open collector) with a 4k7 pull-up to 3V3; the internal pulls are disabled, input hysteresis on |
| AVC-LAN TX | **GP1** | → 2k2 → NPN (e.g. BC547) base; **HIGH = drive the bus dominant** |
| status LED | GP16 | the WS2812 on the Zero boards (`PICO_DEFAULT_WS2812_PIN` if the board defines it) |

The AVC-LAN pair is differential (Data+ / Data−). The firmware only needs a
logic-level "dominant / recessive" signal on GP0 (a comparator across the pair) and
drives a transistor that pulls the pair dominant from GP1; the analogue front end is
described separately.

**RX polarity.** Depending on how the comparator inputs are wired, GP0 is either
low or high while the bus is dominant. At boot the firmware samples GP0 for ~60 ms
(3000 samples, 20 µs apart) and takes the majority level as *idle*; the opposite
level is dominant. If dominant is low, the GPIO input inverter is switched on, so the
PIO always sees dominant = high. The result is reported as `avc_pol` in
`GATEWAY_READY` (`"lo"` = dominant pulls GP0 low, `"hi"` = dominant drives GP0 high).
Auto-detection is reliable while the bus is asleep or idle; on a busy bus, or to be
sure, force it with `{"id":0,"d":{"a":"avc_cfg","pol":"hi"}}` (or `"lo"`, `"auto"`).
TX polarity is fixed: GP1 HIGH = dominant.

## Build & flash

Needs the [pico-sdk](https://github.com/raspberrypi/pico-sdk) 2.x, the
`arm-none-eabi` GCC toolchain, CMake ≥ 3.13 and Ninja. `build.sh` uses
`$PICO_SDK_PATH` and the tools on `$PATH`, and otherwise falls back to the
`~/.pico-sdk/` layout the official Raspberry Pi Pico VS Code extension installs.

```bash
./build.sh                                   # → build-waveshare_rp2040_zero/avclan_rp2040.uf2
PICO_BOARD=waveshare_rp2350_zero ./build.sh  # → build-waveshare_rp2350_zero/avclan_rp2040.uf2
./test/run.sh                                # host unit tests (any C compiler)
python3 test/pio_sim.py                      # PIO timing simulation (after a build)
```

Built with pico-sdk 2.2.0 and Arm GNU Toolchain 14.2.Rel1 (Release):

| Board | UF2 | flash image (.bin) |
|---|---|---|
| `waveshare_rp2040_zero` | 122 880 bytes (120 KiB) | 61 428 bytes |
| `waveshare_rp2350_zero` | 117 760 bytes (115 KiB) | 58 528 bytes |

**Flash:** hold BOOT while plugging the board in (or send `{"id":0,"d":{"a":"bootsel"}}`
to a running board), then copy the `.uf2` onto the `RPI-RP2` (RP2040) or `RP2350`
drive that appears. The board reboots into the firmware.

The device enumerates as a USB CDC-ACM serial port (VID `2E8A`, PID `000A`,
manufacturer "AVC-LAN", product "AVC-LAN Transceiver", serial = the chip's unique id),
e.g. `/dev/serial/by-id/usb-AVC-LAN_AVC-LAN_Transceiver_<id>-if00` on Linux. The
baud rate is ignored.

### Status LED

| Colour | Meaning |
|---|---|
| green, breathing | idle, a host has the port open (DTR set) |
| blue, breathing | idle, no host |
| cyan flash (40 ms) | an AVC-LAN frame was delivered to the host |

The LED is only updated while the bus is quiet (the bit-banged WS2812 write masks
interrupts for ~30 µs, which must not delay an ACK stretch).

## The AVC-LAN frame as implemented

After the start bit, MSB first:

```
broadcast(1) | master(12) P | slave(12) P A | control(4) P A | length(8) P A | { data(8) P A } × length
```

* `broadcast` bit: **0 = broadcast**, 1 = individual (unicast) frame.
* `P` = parity bit = XOR of the field's bits (even parity over field + P).
* `A` = ACK slot: the transmitter sends a '1'; an addressed slave acknowledges by
  stretching it into a '0'. The master address has no ACK slot. In broadcast
  frames nobody acknowledges and the slots are ignored.
* `length` = number of data bytes; the firmware accepts 0..32 (more is a `length` error).

Bits are pulse-width coded; every bit starts with a dominant pulse in a 39 µs slot:

| Symbol | dominant | recessive | RX classification (default thresholds, configurable) |
|---|---|---|---|
| start bit | 166 µs | 19 µs | 100 ≤ w < 400 µs |
| '1' | 20 µs | 19 µs | 6 ≤ w < 26 µs |
| '0' | 32 µs | 7 µs | 26 ≤ w < 100 µs |
| glitch | — | — | w < 6 µs (ignored) |
| stuck | — | — | w ≥ 400 µs (aborts the frame) |

A frame on the wire lasts `166 + 19 + 39 × nbits` µs, with `nbits = 44 + 10 × length`
(a 7-byte frame ≈ 4.6 ms). A start bit always resynchronises the decoder, even mid-frame;
a parity error drops the frame; a frame with no dominant pulse for 600 µs is abandoned.

**Receive path.** The RX PIO (4 MHz, 0.5 µs resolution, ~1 µs debounce) pushes one word
per edge: the dominant width the moment the dominant level ends, and the gap width when
the next one starts. The PIO interrupt (highest priority) classifies widths, runs the
bit decoder and finishes the frame on its last ACK slot; the main loop writes the JSON
line and flushes it in the same iteration. In the PIO simulation the last word reaches
the CPU ≈ 1.75 µs after the last edge; end-to-end latency to the host is dominated by
the USB poll interval (≤ 1 ms).

**Transmit path.** The TX PIO (1 MHz) is DMA-fed and generates the exact timings in the
table. A frame starts only when no frame is being received and the bus has been free of
dominant pulses for 250 µs (otherwise it is deferred, counted in `tx_deferred`, and
retried on the next loop pass). Up to 8 frames are queued. ACK slots are sent as '1'
and left for the slave to stretch. There is no arbitration-loss detection: if another
node starts at the same moment the frame is simply corrupted on the wire. Every frame
we send is also received through GP0 and reported with `"echo":1`; `"nak":1` on that
echo means the addressed slave did not acknowledge (at least one ACK slot stayed '1').

## USB protocol (NDJSON)

Both directions use one JSON object per line (`\n` or `\r` terminated), with the envelope

```
{"id": <device>, "d": { ... }}
```

`id` 0 = system, `id` 2 = AVC-LAN. (Other ids answer `UNKNOWN_DEVICE`; the numbering
is kept from the multi-bus firmware, where 1 was CAN.) Errors are always reported on
the system channel as `{"id":0,"d":{"err":"<CODE>"}}`.

Lines are written whole or not at all: when no host has the port open (DTR low) or
the host is not reading and the 8 KiB USB TX buffer is full, the line is **dropped**
(not queued) and counted in `drop` / `stats.usb.dropped`. A host should therefore
open the port before the bus wakes up and keep reading.

### Messages the firmware emits

**AVC-LAN frame** (one per received frame):

```json
{"id":2,"ts":123456,"seq":17,"d":{"m":"110","s":"178","c":15,"d":["00","12","58","8F"]}}
{"id":2,"ts":123470,"seq":18,"d":{"m":"110","s":"FFF","c":15,"d":["12","01","00"],"b":1}}
{"id":2,"ts":123475,"seq":19,"d":{"m":"178","s":"110","c":15,"d":["00","01","12","10","58","24","85"],"echo":1}}
```

| Field | Meaning |
|---|---|
| `ts` | firmware time in ms since boot when the frame's last bit ended (32-bit, wraps after ~49.7 days) |
| `seq` | 16-bit line sequence number (wraps at 65536), present while `seq` is enabled (default); a gap = lines lost |
| `d.m` | master (sender) address, 3 upper-case hex digits |
| `d.s` | slave (destination) address, 3 hex digits (`FFF`, `1FF`, … for broadcasts) |
| `d.c` | control field, decimal 0..15 (normally 15) |
| `d.d` | data bytes, each a 2-digit upper-case hex string |
| `d.b` | `1` = broadcast frame (absent otherwise) |
| `d.nak` | `1` = individual frame with at least one unacknowledged ACK slot |
| `d.echo` | `1` = this is our own transmission seen back on the bus (matched against the last frame sent, within 5 ms of its end) |

**System messages** (`id` 0):

| Message | When | Example / fields |
|---|---|---|
| `GATEWAY_READY` | ~300 ms after boot (lost if no host has the port open yet) | `{"id":0,"d":{"msg":"GATEWAY_READY","ver":"3.2.0","role":"avclan","cores":1,"fw":"c-sdk","board":"waveshare_rp2040_zero","avc_pol":"lo"}}` |
| `GW_HB` | every 1 s | `{"id":0,"d":{"msg":"GW_HB","role":"avclan","ver":"3.2.0","n":12,"up":12,"avc":340,"avc_err":0,"avc_lvl":1,"drop":0}}` — `n` 8-bit counter, `up` s since boot, `avc` frames delivered, `avc_err` parity + length errors + timeouts, `avc_lvl` raw GP0 level now, `drop` lines dropped |
| `IDENT` | reply to `whoami` | `{"id":0,"d":{"msg":"IDENT","role":"avclan","ver":"3.2.0"}}` |
| `CFG_UPDATED` | reply to every setting command | `{"id":0,"d":{"msg":"CFG_UPDATED","avc_cfg":{"pol":"hi","glitch":6,"t1":26,"t0":100,"tstart":400,"ack":"178"}}}` |
| `stats` | reply to `stats` | see below |
| `avc_raw` | while raw mode is on | `{"id":0,"d":{"avc_raw":[166,-19,20,-19,32,-7]}}` — dominant widths positive, gaps negative, µs; ≤ 96 values per line; `"dropped":n` if the 1024-entry ring overflowed |
| `avc_err` | while error reporting is on | `{"id":0,"d":{"avc_err":"parity","field":"slave","m":"110","s":"000"}}` — field ∈ idle, bcast, master, slave, control, length, data |
| `err` | on any error | `{"id":0,"d":{"err":"BAD_AVC_HEADER"}}` |
| `RESET`, `BOOTSEL` | before rebooting | `{"id":0,"d":{"msg":"RESET"}}` |
| `log` | with `log_rx` on | `{"id":0,"d":{"log":"USB_RX","dev":2,"a":"auto"}}` |

`stats` reply:

```json
{"id":0,"d":{"stats":{
  "avc":{"frames":340,"echo":12,"parity":0,"length":0,"aborted":3,"timeouts":0,"stray":0,"glitch":5,
         "ring_ovf":0,"words":31000,"tx":12,"tx_deferred":4,"tx_qfull":0,"tx_auto":2,"acks":96,"ack":"178","pol":"hi"},
  "usb":{"lines":420,"dropped":0,"rx_lines":9,"rx_overlong":0,"connected":1}}}}
```

`aborted` = frames cut by a new start bit / stuck bus / timeout, `stray` = bit pulses
outside a frame, `glitch` = pulses shorter than `glitch`, `ring_ovf` = decoded frames lost
because the main loop lagged (32-entry ring), `words` = PIO words processed, `acks` =
ACK slots stretched.

Error codes: `CMD_ERR` (line has no `id`), `JSON_PARSE` (with `code`, jsmn error),
`UNKNOWN_DEVICE`, `BAD_AVC_HEADER`, `BAD_AVC_DATA`, `BAD_AUTO_SLOT`, `AVC_TX_QUEUE_FULL`.

### Commands the firmware accepts

Numbers: addresses and data bytes are **hex strings** (`"178"`, `"0x178"` also works);
a bare JSON number is read as decimal. The control field `c` is decimal. A command
line may be at most 4096 bytes and 200 JSON tokens.

**Transmit a frame** (`id` 2, no `a`):

```json
{"id":2,"d":{"m":"178","s":"110","c":15,"d":["00","58","12","52","02","01"]}}
{"id":2,"d":{"m":"178","s":"1FF","c":15,"d":["58","31","F1","02","00"],"b":true}}
```

`b` sets the broadcast bit; default is broadcast only when `s` is `FFF`. There is no
reply on success: the frame comes back on RX tagged `"echo":1`. Errors:
`BAD_AVC_HEADER`, `BAD_AVC_DATA` (more than 32 bytes or a byte > FF), `AVC_TX_QUEUE_FULL`.

**AVC-LAN configuration** (`id` 0, any subset of the keys):

```json
{"id":0,"d":{"a":"avc_cfg","pol":"hi"}}
{"id":0,"d":{"a":"avc_cfg","ack":"178"}}
{"id":0,"d":{"a":"avc_cfg","t1":26,"t0":100,"tstart":400,"glitch":6}}
```

| Key | Meaning |
|---|---|
| `pol` | `"auto"` (re-detect, ~60 ms), `"hi"`, `"lo"` — restarts the receiver (undelivered frames are discarded) |
| `ack` | slave address whose ACK slots the firmware stretches, `"000"` = off (default); an invalid value also turns it off |
| `glitch`, `t1`, `t0`, `tstart` | classification thresholds in µs (see the timing table) |

Always answered with the full `CFG_UPDATED` `avc_cfg` object.

**Auto-reply table** (`id` 2, `a:"auto"`, 4 slots):

```json
{"id":2,"d":{"a":"auto","slot":0,"on":true,"m":"110","s":"FFF","d":["12","01","00"],
             "tx":{"m":"178","s":"110","c":15,"d":["00","01","12","10","58","24","85"]}}}
{"id":2,"d":{"a":"auto","slot":0,"on":false}}
{"id":2,"d":{"a":"auto"}}
```

A slot matches a received frame when its master `m` and slave `s` match (either may be
omitted = any) and the frame's data **starts with** `d` (0..8 bytes). The `tx` frame is
then queued immediately in the firmware. Replies: `{"id":2,"d":{"auto":0,"on":true}}`,
`{"id":2,"d":{"auto":0,"on":false}}`, and for the listing
`{"id":2,"d":{"auto":[{"slot":0,"on":true,"hits":3},…]}}` (hits reset when a slot is set).
Several slots may fire on one frame. Matching also sees our own echoes, so a reply must
not match its own slot. Errors: `BAD_AUTO_SLOT`, `BAD_AVC_HEADER`, `BAD_AVC_DATA`.

**Other system commands** (`id` 0):

| Command | Effect |
|---|---|
| `{"id":0,"d":{"a":"whoami"}}` (also `"identify"`, `"id"`) | `IDENT` reply |
| `{"id":0,"d":{"a":"stats"}}` | counters |
| `{"id":0,"d":{"a":"avc_raw","on":true}}` | stream raw pulse widths (PHY bring-up); `false` stops |
| `{"id":0,"d":{"a":"avc_err","on":true}}` | report every parity/length error with the field it died in |
| `{"id":0,"d":{"seq":false}}` | drop the `seq` field from frame lines (`true` restores) |
| `{"id":0,"d":{"a":"log_rx","on":true}}` | acknowledge every received command with a `USB_RX` log line |
| `{"id":0,"d":{"test":"avc"}}` | loopback: GP0 level before / while / after driving GP1 dominant for 100 µs → `{"test":"avc","rx_idle":1,"rx_drive":0,"rx_after":1}` (disturbs the bus) |
| `{"id":0,"d":{"test":"tx_high"}}` / `"tx_low"` | hold GP1 dominant / recessive (bench only; the next transmission returns the pin to the PIO) |
| `{"id":0,"d":{"a":"reset"}}` | watchdog reboot |
| `{"id":0,"d":{"a":"bootsel"}}` | reboot into the UF2 bootloader |

Unknown `id` 0 actions are ignored. A watchdog (8 s) reboots the board if the main loop stalls.

## Emulating an ECU: ACK stretch and auto-reply

Both features are off by default; without them the firmware is a passive logger plus
a host-driven transmitter.

**Why the ACK stretch is needed.** On IEBus a unicast frame is only completed if the
addressed slave acknowledges *every* ACK slot (after the slave address, control,
length and each data byte). If nobody does, the master gives up after the slave
address field and retries: the frame never carries its data, so the host would never
see what the master wanted. When the real ECU is removed (for example to emulate the
navigation ECU at address `178`), something else has to acknowledge in real time —
an ACK decision is due ~19 µs after the parity bit, far below a USB round trip.
With `{"a":"avc_cfg","ack":"178"}` the receive interrupt does it: for every individual
frame whose slave address is `178`, after each parity bit it drives GP1 dominant from
6 µs to 30 µs into the ACK slot (the master's own '1' pulse covers 0..20 µs; with the
driver's ~2 µs tail the slot reads as a 32 µs '0' = ACK). It is skipped while we are
transmitting. Only one address can be acknowledged. Counted in `stats.avc.acks`.
Without it, a display talking to an emulated nav ECU was observed to produce 464
aborted `110→178` headers in 40 s.

**Why the auto-reply is needed.** Some exchanges must be answered faster than the host
can: the display's startup roll call (`110 → FFF  12 01 00`) must be answered within
about a millisecond — the real nav ECU answers in ~0.5 ms, while a reply from the host
after the USB round trip (~2.5 ms) lands on top of another ECU's (the climate
controller's) answer and is lost. An auto-reply slot queues the answer from the main
loop before the frame is even written to USB; it leaves after the minimum 250 µs of
bus silence, ≈ 0.3 ms after the triggering frame ended. The host still sees both the
trigger and the reply (as an echo).

`tools/nav_emu.py --fw-auto --fw-ack` uses both: slot 0 answers `12 01 00`, slot 1
answers `12 01 01`, and the ACK address is set to `178`.

## Limits and constants

| Item | Value |
|---|---|
| data bytes per frame | 32 (RX and TX) |
| decoded-frame ring (IRQ → main loop) | 32 frames |
| TX queue | 8 frames |
| auto-reply slots / match prefix | 4 / 8 bytes |
| raw-pulse ring / values per line | 1024 / 96 |
| decode-error ring | 8 (excess errors are not reported) |
| command line | 4096 bytes (longer lines discarded, `rx_overlong`), 200 JSON tokens |
| USB CDC buffers | TX 8192 bytes, RX 1024 bytes |
| frame abandon timeout | 600 µs without a dominant pulse |
| bus idle before TX | 250 µs |
| polarity detection | 3000 samples × 20 µs |
| heartbeat / watchdog | 1 s / 8 s |

## Licence

MIT, see `../LICENSE`. `src/jsmn.h` is jsmn by Serge A. Zaitsev (MIT, `src/jsmn_LICENSE`).
`pico_sdk_import.cmake` is copied from the pico-sdk (BSD-3-Clause, Raspberry Pi Ltd).
