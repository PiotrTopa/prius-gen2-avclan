# 2. Devices, roll call and re-registration

Verification tags: **USER** = the operator confirmed it on the car's display or behaviour at
capture time; **TX** = we transmitted it (emulating a unit) and the car accepted it; **DECODE**
= consistent across all captures; **PRIOR** = the name comes from published prior art (see
the README's references); **INF** = our inference. Dates are capture dates.

## 2.1 Physical units seen on this car

Over 142 777 decoded frames (2026-10-07 to 2026-10-19), the only masters on the bus were
`110`, `178` and `1C6`.

| Address | Unit (this car) | Name in prior art | Logical devices it announces | Verified |
|---|---|---|---|---|
| `110` | Multi-display (touch screen, "EMV"). It runs the roll call | EMV (PRIOR) | communication control (`12`), drawing functions `5D 5F 56 55 …`, switches `21 25` | DECODE + USER, 2026-10-07 |
| `178` | Navigation ECU (factory DVD nav box) | NAVI (PRIOR) | `58 24 85` (roll call) | DECODE; unplug test 2026-10-07; emulated 2026-10-14 (TX) |
| `1C6` | Gateway ECU: climate status and trip / energy monitor data | G/W (PRIOR) | `E0 E4 E5` (roll call) | DECODE |
| `1FF` | broadcast (status) | — | — | DECODE |
| `FFF` | broadcast (system) | — | — | DECODE |

Not present on this car's bus: no `190`/`160` audio head unit, no `440` DSP amplifier or `480`
amplifier, no tuner or CD changer. See [07-what-is-not-on-the-bus.md](07-what-is-not-on-the-bus.md).
The factory head unit had been replaced with an aftermarket radio before these captures, which
may be why no audio master appears.

Two frames were addressed to `100` and `113`. Each was a bit-corrupted copy of a known frame,
so ignore them.

## 2.2 Logical device IDs

"Seen" means the ID appears as `from`/`to` in data bytes on this car. Names in the third column
come from prior art (the Corolla AVC-LAN list). "Agrees" means our observations fit that name.

| ID | Role on this car | Prior-art name | Agrees? | Verified |
|---|---|---|---|---|
| `01` | communication control (roll call, broadcasts) | communication ctrl | yes | DECODE |
| `12` | display's communication manager | communication | yes | DECODE |
| `21` | touch panel (`21 → 24`, opcode `78`) | SW | yes | DECODE + USER |
| `24` | nav-side receiver of touch coordinates (hosted by 178) | SW converting | yes | DECODE |
| `25` | hardware/soft switches (`25 → 58` nav keys, `25 → E0` climate keys) | command SW | yes | DECODE + USER + TX |
| `31` | broadcast "listeners" target (`58 31 F1`, `E4 31 B6`) | — | — | DECODE |
| `32`, `34`, `6E` | display functions that the nav sets up (`E0`/`F0` handshakes) | `34` front passenger monitor | unclear | DECODE |
| `55` | telephone screen (built into the display) | Bluetooth tel | yes | USER, 2026-10-14 |
| `56` | information screen | information drawing | yes | USER |
| `58` | navigation | navigation ECU | yes | USER + TX |
| `5D` | climate screen | climate ctrl drawing | yes | USER |
| `5E` | audio screen | audio drawing | yes | USER |
| `5F` | energy monitor / trip ("consumption") screen | trip info drawing | yes | USER |
| `85` | nav-side climate subscriber (hosted by 178) | voice control | **differs**: here 85 only subscribes to climate data (`85 → E0`) | DECODE |
| `E0` | climate control device (hosted by 1C6) | climate ctrl dev | yes | DECODE + TX |
| `E4` | energy/drive data source (hosted by 1C6) | — (not listed) | new | DECODE + USER |
| `E5` | trip information (hosted by 1C6) | trip info | yes | DECODE |

IDs listed in the nav's device tables but never used in traffic on this car: `27 28 29 40 43 44
45 60 61 62 63 64 65 6D 74 A2 A4`. Prior art names `28` beep in head unit, `29` beep via
speakers, `60` tuner, `61` tape, `62` CD, `63` CD changer, `74` audio amplifier. The factory nav
box therefore claims audio functions (tuner `60`, amplifier `74`) in its table.

## 2.3 Startup roll call (cold bus)

The display (110) runs it within about the first second after the bus wakes. The sequence below
is the **genuine nav**, captured 2026-10-07 (`run1`) and 2026-10-14 (`realnav_full`). Times
are frame-end timestamps relative to the roll-call broadcast (1 ms resolution). A full excerpt
is in [`examples/01_rollcall_real_nav_cold_start.csv`](../examples/01_rollcall_real_nav_cold_start.csv).

| t (ms) | Frame | Meaning | Verified |
|---|---|---|---|
| 0 | `110→FFF 12 01 00` (B) | roll call: "who is there?" | DECODE |
| ≈ 5 | `178→110 00 01 12 10 58 24 85` | nav: "I host 58, 24, 85" | DECODE + TX |
| ≈ 10 | `1C6→110 00 01 12 10 E0 E4 E5` | gateway: "I host E0, E4, E5" | DECODE |
| ≈ 1020 | `110→FFF 12 01 01` (B) | device-table request | DECODE |
| ≈ 1025 | `178→110 00 01 12 12 58 28 29 32 60 74 A4 56` | nav device table | DECODE + TX |
| ≈ 1030 | `1C6→110 00 01 12 12 5D 00 5F 32` | gateway device table | DECODE |
| ≈ 1050 | `110→1C6 00 01 E5 8C` → `1C6→FFF E5 01 9C 57 42 4C 41 45 4E` (B) | trip-info registration (the last six bytes are ASCII `WBLAEN`; meaning unknown) | DECODE |
| ≈ 1070 | `110→FFF 12 01 46` (B) | "any device in use" (prior art agrees, sent by a head unit there) | DECODE + PRIOR |
| ≈ 1100 | `110→FFF 12 01 60 00 05 00 05` (B) | active screen = none yet | DECODE |
| ≈ 1110 | `110→178 00 12 58 8F` | nav identification request ([05](05-nav-emulation.md)) | DECODE + TX |
| ≈ 1130 | `110→1C6 00 12 01 02 11 00 11 01 11 02 11 03` | per-unit table query to the gateway (no reply seen) | DECODE |
| ≈ 1135… | `110→178 00 12 01 02 …` ×3 | per-unit table queries to the nav ([05](05-nav-emulation.md)) | DECODE + TX |

Rules learned (2026-10-07 unplug test and 2026-10-14 emulation):

- **The roll-call reply is the gate.** With the nav unplugged, the display sends **no** frame to
  `178` at all: no probing, and no MENU/DEST/MAP or touch frames. Everything nav-related
  depends on `12 10 58 24 85` arriving in reply to `12 01 00` (DECODE, 2026-10-07).
- The genuine nav answers within ≈ 0.5 ms of the end of the roll call, before the gateway
  (≈ 2.5 ms). An answer that starts later collides with the gateway's reply. An answer at
  +20 ms registered, but the display only progressed once our receiver also ACKed in real time
  (TX, 2026-10-14).
- The display then calls the nav (`00 12 58 8F`) ≈ 1.12 s after the roll call. If nobody ACKs
  that frame, it retries every 25 ms indefinitely ([01](01-bus-basics.md#14-acknowledge-ack-behaviour)).

## 2.4 Re-registration and late joiners

| Frame | Period | Meaning | Verified |
|---|---|---|---|
| `110→FFF 12 01 20 XX` (B) → each unit `00 01 12 30 XX YY` | 60 s | presence ping. XX goes up by 1 per ping; replies echo XX. YY = `FF` from the nav, and from 1C6 in every capture from 2026-10-14 on. YY = `00` from 1C6 in every 2026-10-07 capture (meaning unknown) | DECODE + TX |
| `110→1C6 00 01 E5 8C` → `1C6→FFF E5 01 9C 57 42 4C 41 45 4E` (B) | 60 s | trip-info re-registration | DECODE |
| `1C6→110 00 E4 5F BA nn` | 60 s | unknown (nn 00…07) | DECODE |
| `178→1FF 01 12 13 58 24 85` (B) | once | **late announcement**: a nav that was still booting at the roll call announces its logicals | DECODE, 2026-10-14 |
| `110→178 00 12 01 03`, then `110→FFF 12 01 01` and the whole table/setup dialogue again | — | the display's reaction to the late announcement: it re-runs the setup for that unit | DECODE, 2026-10-14 |

A nav that boots slowly (the genuine one needs ≈ 20 s) gives truncated answers at the roll call,
such as `00 01 12 10 58 24` and `00 58 12 F0 80`. The display then sets up with defaults.
About 20 s later the nav sends the late announcement above, and the display re-runs the
dialogue. This is how the genuine nav ends up switching the display language a few seconds
after start ([05](05-nav-emulation.md#54-language-byte)).
