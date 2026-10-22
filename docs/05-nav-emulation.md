# 5. Making the display accept a navigation unit (178 emulation)

This chapter is the dialogue a replacement "nav" must hold with the display (110) so that the
display:

- registers it,
- sends it the MENU/DEST/MAP keys and the touch coordinates,
- switches to its video input (screen 58) on request, and
- uses the UI language it chooses.

All of it was verified in the car on **2026-10-14** and again on **2026-10-19**. The factory
nav box was unplugged, and a microcontroller on the bus answered as `178`. The genuine nav was
captured for reference on 2026-10-07 and 2026-10-14.

Tags: **REAL** = observed from the genuine nav; **TX** = sent by our emulator and accepted by
the display; **REQ** = without it the emulation demonstrably failed; **INF** = our choice or
inference, works but is unconfirmed.

## 5.1 Hard requirements

| # | Requirement | Evidence |
|---|---|---|
| 1 | **ACK every frame addressed to 178 in real time** (stretch the ACK slots, [01 §1.4](01-bus-basics.md#14-acknowledge-ack-behaviour); measured with the RP2040 transceiver firmware: dominant from 6 to 30 µs into each slot) | REQ: without it the display aborts its `00 12 58 8F` call at the address ACK and retries every 25 ms (464 attempts in 40 s). The nav menu never appears |
| 2 | **Answer the roll call `12 01 00` within ≈ 0.5 ms**, before the gateway 1C6 (≈ 2.5 ms) | REQ: an answer at 8 ms collided and was NAKed. The answer must come from the transceiver's own firmware, not a USB host. Measured with the RP2040 transceiver firmware, its auto-reply leaves ≈ 0.3 ms after the roll call ([01 §1.7](01-bus-basics.md#17-timing-as-measured-with-the-rp2040-transceiver-firmware)) |
| 3 | Answer `12 01 01` (device table) just as quickly | TX (same mechanism) |
| 4 | Broadcast `58 31 F1 02 00` **only while the display shows screen 58** | REQ: unconditional broadcasts made the display send `43 02 00` (110 times) and show "external device not working correctly" |
| 5 | Answer the screen release `43 02 00` with `53 02 00` | TX: without it the display needs ≈ 3.5 s to leave the nav screen; with it ≤ 1 s |
| 6 | Answer the 60 s ping `12 01 20 XX` with `00 01 12 30 XX FF` | TX (a missed or NAKed reply had no visible effect) |

With the tools in this repository, `tools/nav_emu.py --fw-auto --fw-ack` implements all six
requirements. `--fw-auto` stores the roll-call replies in the transceiver firmware and
`--fw-ack` makes it ACK frames addressed to 178. The serial port comes from `AVC_PORT`, and
`--pol` defaults to auto-detection.

## 5.2 Cold-start sequence (emulator, as accepted 2026-10-14)

Times are relative to the roll-call broadcast. "→ reply" lines are what the emulator sends.

```
t=0      110→FFF 12 01 00                               roll call (B)
         → 178→110 00 01 12 10 58 24 85                 within 0.5 ms (hosts 58, 24, 85)
t≈1.02s  110→FFF 12 01 01                               device table (B)
         → 178→110 00 01 12 12 58 28 29 32 60 74 A4 56
t≈1.10s  110→178 00 12 58 8F                            identification
         → 178→110 00 58 12 9F 02 F9 D1 13 0A 58 A6 9A 80 80
t≈1.13s  110→178 00 12 01 02 17 80 11 03 11 07          per-unit table 1
         → 178→110 00 01 12 12 27 58 40 64 62 61 55 6E 6D
t≈1.18s  110→178 00 12 01 02 17 81 11 06 11 07 11 08    per-unit table 2
         → 178→110 00 01 12 12 34 A2 58 43 63 65 44 45 E0
t≈1.20s  110→178 00 12 01 02 11 00 17 82 1C 68          per-unit table 3 (no direct reply)
         → initial burst (5.3)
t≈1.26s  110→FFF 00 01 07                               (B)
         → 178→110 00 01 00 17
t≈1.31s  110→178 00 32 58 E0      → 178→110 00 58 32 F0 C9 00 00 01
t≈1.43s  110→178 00 56 58 8E      → time reply (5.5)
t≈2.6s   110→178 00 6E 58 E0      → 178→110 00 58 6E F0 C9 00 00 01
t≈2.7s   110→178 00 32 58 F0 00 00 00 02  → 178→110 00 58 56 B7 LL   (language, 5.4)
t≈3.2s   110→178 00 56 58 F0 49 3C 44     → 178→110 00 58 56 B7 LL
         110→178 00 34 58 F0 00 01        (no reply)
```

All byte strings are those of the genuine nav (REAL), replayed verbatim (TX). See
[`examples/01_rollcall_real_nav_cold_start.csv`](../examples/01_rollcall_real_nav_cold_start.csv)
for the genuine nav and
[`examples/06_rollcall_amp_powered.csv`](../examples/06_rollcall_amp_powered.csv) for the
emulator.

**Identification blob (`9F`).** The genuine nav sent two different payloads on different days:
`02 F9 D1 3D 0A 58 A6 E4 80 8C` (2026-10-07) and `02 F9 D1 13 0A 58 A6 9A 80 80` (2026-10-14,
before and after a language change). Either one replayed verbatim was accepted (TX). The
display polls `00 12 58 8F` again every 30 s. The meaning of the bytes is unknown.

## 5.3 Initial burst (nav-initiated subscriptions)

Immediately after per-unit table 3, the nav sends:

```
178→110 00 58 32 E0
178→1C6 00 85 E0 E0      ← 1C6: 00 E0 85 F0 00 71
178→110 00 58 56 E0
178→110 00 58 34 E0      (the display NAKs this one; harmless, seen every time)
178→1C6 00 85 E0 E4      ← 1C6: 00 E0 85 F4 <climate status, 6 bytes>
178→1C6 00 85 E0 E6      ← 1C6: 00 E0 85 F6 <set temperature, 2 bytes>
```

The genuine nav repeats `00 58 32 E0`, `00 58 56 E0` and `00 58 34 E0` every ≈ 300 ms, three
times or until the display has answered. The display's answers are the `F0` frames of 5.2
(`32 58 F0 …`, `56 58 F0 …`, `34 58 F0 …`), in line with the "+0x10" reply rule (INF). Whether
the nav's climate subscription (`85 → E0`) is needed for anything except the nav's own climate
display is unknown. Our emulator sends it because the genuine nav does (TX).

## 5.4 Language byte

The nav's answer `178→110 00 58 56 B7 LL` (to the display's `56 58 F0 49 3C 44` and
`32 58 F0 00 00 00 02`) **sets the display's whole UI language**. The display confirms it in
its 5-second broadcast `110→FFF 56 01 B9 LL 00 FF`.

| LL | Language | Verified |
|---|---|---|
| `02` | English | REAL (2026-10-14) + TX: emulator cold start with `02` was English from the first second |
| `06` | Dutch | REAL (2026-10-07) + TX: replaying `06` turned the display Dutch ("TAAL" = language) |

Other values were not tried. When a nav is registered, the nav owns this setting: a language
chosen on the display without a nav was overridden instantly when the emulator announced
itself with `06` (USER, 2026-10-14).

Why the genuine nav seemed to switch language by itself: it was still booting at the roll call.
The display set up with its default, then the nav's late announcement `178→1FF 01 12 13 58 24
85` triggered a fresh setup, and that one got `B7 02` ([02 §2.4](02-devices.md#24-re-registration-and-late-joiners)).

The "Language" soft key on the info page sends `00 25 58 80 40 00 00`. We do not know the reply
the nav uses to draw its language list; with no answer the key lights for ≈ 3 s and nothing
happens.

## 5.5 Time reply

`110→178 00 56 58 8E` every 5 s. Reply `178→110 00 58 56 9E 00 PP 01 HH MM SS FF`, with HH MM SS
in **BCD**.

| Observed | Notes |
|---|---|
| 2026-10-07: `00 03 01 23 29 25 FF` … `23 31 03` | SS goes up by 5 per poll |
| 2026-10-14: `00 01 01 00 00 17 FF` … | counted from 00:00:00 when the nav page was first opened |
| during the genuine nav's boot: `8F 01 99 74 00 00 D2` | not ready |

Both PP = `03` and PP = `01` forms were accepted with any running clock (TX). Generate the
value; do not replay a fixed one. What the clock represents (GPS time, elapsed time) is unknown.

## 5.6 Screens and keys in steady state

| Event | Display sends | Nav replies | Verified |
|---|---|---|---|
| MENU / DEST / MAP pressed | `00 25 58 84 KK 00` (+ release `00 00`) | `00 58 12 50 02 01` (screen request) | REAL + TX |
| info soft key Maintenance/Calendar/Language | `00 25 58 80 KK 00 00` | `00 58 12 50 02 01` | REAL |
| display offers the screen | `00 12 58 42 02 01` | `00 58 12 52 02 01` + `178→1FF 58 31 F1 02 00` | REAL + TX |
| display on screen 58 | `12 01 60 58 01 00 05` every 5 s | `178→1FF 58 31 F1 02 00` every 5 s, ≈ 0.6 s before the DB heartbeat | REAL + TX |
| user leaves the nav screen | `00 12 58 43 02 00` | `00 58 12 53 02 00` + `178→1FF 58 31 F1 00 00` | REAL + TX |
| touch on screen 58 | `00 21 24 78 X Y X Y` | none | REAL |
| ping (60 s) | `12 01 20 XX` (B) | `00 01 12 30 XX FF` | REAL + TX |
| time (5 s) | `00 56 58 8E` | 5.5 | REAL + TX |
| identification (30 s) | `00 12 58 8F` | `9F` blob | REAL + TX |

Heartbeat: the genuine nav broadcasts `178→FFF 58 01 DB 00 00 00 00 00 00` every 5 s **even
while the display shows another screen** (REAL, 2026-10-14, display on screen 5F). The screen
claim `58 31 F1 02 00` is the broadcast that must be suppressed when the display is not on 58.
To be safe, our emulator sends both only while on 58, and that works (TX).

## 5.7 What the display NAKs or ignores (harmless)

- `00 58 34 E0` in the initial burst: NAKed at every cold start (genuine nav and emulator).
- Occasional NAK of a `00 01 12 30 XX FF` ping reply or of a `9F` ident reply: no visible
  effect. The ident is polled again within 30 s.
- `00 34 58 F0 00 01` from the display needs no reply.

## 5.8 Nothing else depends on 178

In every capture the nav talked only to the display, plus its climate subscription to 1C6 and
its two broadcasts. With the emulator in place the factory nav box can be removed. The display
still shows climate, energy monitor and info, and it shows the emulator's video on screen 58
(2026-10-14 and 2026-10-19).
