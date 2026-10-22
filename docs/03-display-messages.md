# 3. What the display (110) sends and receives

Verification tags: **USER** = the operator confirmed it on the car (screen, button, effect)
while capturing; **TX** = we transmitted it, or answered it, and the display behaved as
described; **CAN** = correlated with CAN data; **DECODE** = consistent structure and period
over all captures, meaning not confirmed; **INF** = inferred. Dates are capture dates.

## 3.1 Active screen broadcast

`110→FFF 12 01 60 SS MM 00 05` (B), every ≈ 5 s and on every screen change.

| SS | Screen | Verified |
|---|---|---|
| `58` | navigation (nav picture shown; MM = `01`) | USER, 2026-10-07 and 2026-10-14; TX |
| `5F` | energy monitor / consumption (trip) | USER, 2026-10-07 |
| `5D` | climate | USER, 2026-10-07 |
| `5E` | audio (no audio unit on this car) | USER, 2026-10-07 |
| `56` | information menu | USER, 2026-10-07 |
| `55` | telephone (the display's built-in Bluetooth page) | USER, 2026-10-14 |
| `00` | none yet (during startup) | DECODE |

SS is the **logical ID of the function that draws the screen** ([02](02-devices.md#22-logical-device-ids)).
MM was `01` for the nav screen and `05` for all of the display's own screens (DECODE). The
meaning of MM and of the trailing `00 05` is unknown.

## 3.2 Periodic broadcasts from the display

| Frame | Period | Meaning | Verified |
|---|---|---|---|
| `110→FFF 12 01 60 SS MM 00 05` | 5 s | active screen (3.1) | USER |
| `110→FFF 12 01 46` | 5 s | "any device in use" (name from prior art) | DECODE + PRIOR |
| `110→FFF 56 01 B9 LL 00 FF` | 5 s | UI language currently in use, LL as in [05](05-nav-emulation.md#54-language-byte) (`02` English, `06` Dutch) | USER + TX, 2026-10-14 |
| `110→FFF 01 01 5F xx` | 5 s | unknown: xx = `09` (most), `0F`, `0B`, `01`. Not correlated with the light switch | DECODE |
| `110→FFF 12 01 20 XX` | 60 s | presence ping ([02](02-devices.md#24-re-registration-and-late-joiners)) | DECODE + TX |
| `110→1C6 00 01 E5 8C` | 60 s | trip-info re-registration | DECODE |
| `110→178 00 56 58 8E` | 5 s, only when a nav is registered | time request ([05](05-nav-emulation.md)) | DECODE + TX |
| `110→178 00 12 58 8F` | 30 s, only when a nav is registered | identification poll ([05](05-nav-emulation.md)) | DECODE + TX |

## 3.3 Lights / dimming

| Frame | Meaning | Verified |
|---|---|---|
| `110→FFF 01 01 5B 40` (B) | vehicle lights switched on (parking, low or high beam): display goes to night brightness | USER, 2026-10-07 (one event for parking→low→high) |
| `110→FFF 01 01 5A 80` (B) | lights off: day brightness. Also sent once at every start | USER, 2026-10-07 |

Fog lights, turn indicators and high/low beam changes produce **no** AVC-LAN frame (USER,
2026-10-07).

## 3.4 Touch panel

`110→178 00 21 24 78 X Y X Y` while the display is on the **nav screen (58)** and a nav is
registered. The X Y pair is repeated (bytes 6–7 = bytes 4–5). Frames come at ≈ 10–15 per
second while the finger is down; `00 00 00 00` means released. Coordinates and calibration are
in [06-touch-calibration.md](06-touch-calibration.md). Verified: USER + DECODE, 2026-10-07 and
2026-10-14. The frame format agrees with prior art.

On the display's own screens (climate, energy, info…) touches are handled inside the display.
No coordinates go on the bus; only the resulting command frames appear (climate keys, 3.6).

## 3.5 Nav hardware keys (MENU / DEST / MAP)

`110→178 00 25 58 84 KK 00`; release = `KK = 00`.

| KK | Key | Verified |
|---|---|---|
| `01` | MENU | USER, 2026-10-07 (7 presses = 7 frames) |
| `04` | DEST | USER, 2026-10-07 (9/9) |
| `02` | MAP | USER, 2026-10-07 (10 frames for 11 presses; one press probably not registered) |

These keys are only sent when a nav is registered. Without one, no frame appears at all
(2026-10-07 unplug test). The nav answers a key press with a screen request (3.7).

## 3.6 Info-screen soft keys that belong to the nav

`110→178 00 25 58 80 KK 00 00`: soft keys on the display's info page whose pages the nav draws.

| KK | Key | Verified |
|---|---|---|
| `01` | Maintenance | USER, 2026-10-14 |
| `08` | Calendar | USER, 2026-10-14 |
| `40` | Language | USER, 2026-10-14 |

The genuine nav acknowledges with `178→110 00 58 12 50 02 01` and the display then grants it
the screen (3.7). "Telephone" on the same page is the display's own screen `55`.

Climate keys (`110→1C6 00 25 E0 84 …`) are in [04-climate-and-vehicle.md](04-climate-and-vehicle.md).

## 3.7 Screen request / grant / release (who owns the picture)

The nav box supplies the video for screen 58. Ownership is negotiated explicitly:

| Step | Frame | Verified |
|---|---|---|
| nav asks for the screen (after a key) | `178→110 00 58 12 50 02 01` | DECODE + TX, 2026-10-07/14 |
| display offers the screen | `110→178 00 12 58 42 02 01` | DECODE + TX |
| nav accepts | `178→110 00 58 12 52 02 01` plus broadcast `178→1FF 58 31 F1 02 00` ("my screen is on") | DECODE + TX |
| display switches | `110→FFF 12 01 60 58 01 00 05` within ≈ 30 ms | USER + TX, 2026-10-14 and 2026-10-19 |
| display wants the screen back (user pressed INFO, CLIMATE, …) | `110→178 00 12 58 43 02 00` | USER + TX, 2026-10-14 |
| nav releases | `178→110 00 58 12 53 02 00` plus broadcast `178→1FF 58 31 F1 00 00` ("my screen is off") | DECODE (genuine nav, 2026-10-14) + TX |

- If the nav does not answer `43 02 00`, the display retries once per second for ≈ 3.5 s and
  then switches anyway. The user sees a ≈ 3–5 s lag (USER + TX, 2026-10-14).
- While the nav owns the screen it broadcasts `58 31 F1 02 00` every 5 s. If the nav sends
  that broadcast while the display shows **another** screen, the display answers each one with
  `43 02 00`. It eventually shows "external device not working correctly" (USER + TX, 2026-10-14).
- Example: [`examples/02_screen_switch_emulated_nav.csv`](../examples/02_screen_switch_emulated_nav.csv).

## 3.8 Status exchanges between display and nav

Both sides use opcode `E0` to request a status and receive the answer as `F0` ("+0x10" rule).
The nav sends `00 58 32 E0`, `00 58 56 E0` and `00 58 34 E0` to the display functions `32`,
`56` and `34`. The display sends `00 32 58 E0` and `00 6E 58 E0` to the nav. The pairing of the
display's `F0` frames with the nav's `E0` requests is INF (from opcode and timing).

| Frame | Reply from the genuine nav | Verified |
|---|---|---|
| `110→178 00 32 58 E0` | `00 58 32 F0 C9 00 00 01` | DECODE + TX |
| `110→178 00 6E 58 E0` | `00 58 6E F0 C9 00 00 01` | DECODE + TX |
| `110→178 00 32 58 F0 00 00 00 02` (status of 32) | `00 58 56 B7 LL` (language), sometimes none | DECODE + TX |
| `110→178 00 34 58 F0 00 01` (status of 34) | none | DECODE |
| `110→178 00 56 58 F0 49 3C 44` (status of 56) | `00 58 56 B7 LL` (language) | DECODE + TX |

In `00 56 58 F0 49 3C 44` the last byte equals the raw outside-temperature byte of
[04](04-climate-and-vehicle.md#41-outside-temperature) (`44` = 20 °C), but it did not change
between captures taken at different temperatures, so this is a coincidence or a stale value
(INF). `49` and `3C` are unknown.

## 3.9 Things not observed on this car

- **Beeps.** Prior art shows `110→440 00 5E 29 60 dd` (beep through the amplifier). There is no
  `440` here, and no beep request was seen.
- **Display bezel keys** that select the display's own screens (INFO, CLIMATE, …) send no
  key frame. Their only trace on the bus is the new `12 01 60 SS` broadcast, plus `43 02 00`
  if the nav owned the screen.
