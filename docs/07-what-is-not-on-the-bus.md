# 7. What is NOT on the bus (on this car)

Negative results are as useful as positive ones when you plan a project. Each item below says
how it was tested.

## 7.1 The JBL amplifier does not answer on this AVC-LAN pair

Prior art for other Toyota models shows amplifiers on AVC-LAN (`440` DSP-AMP, `480` AMP), with
balance, fade, bass and beep commands. On this car:

- Across **all** captures (142 777 frames), the only masters are `110`, `178` and `1C6`. No
  frame is addressed to or from `440`/`480`.
- **Roll-call test (2026-10-19).** The amplifier was switched on (its power is controlled from
  the aftermarket radio), the car was power-cycled, and the cold-start roll call was recorded.
  `110→FFF 12 01 00` was answered only by `178` and `1C6`. The device-table round
  (`12 01 01`) likewise had only `178` and `1C6` answering. Excerpt:
  [`examples/06_rollcall_amp_powered.csv`](../examples/06_rollcall_amp_powered.csv).
- Conclusion: the amplifier is not connected to the AVC-LAN pair that links display, nav and
  gateway, or it does not join the bus in this configuration. It is also possible that the
  radio's switch does not actually power it. Volume, balance, fade and
  tone cannot be read or set over this bus here.

The factory nav's device table lists logical `74` (audio amplifier) and `60` (tuner). The nav
box claims these functions in its table, but no frame ever used them.

## 7.2 Aftermarket radio

The factory audio head unit had been replaced by an aftermarket unit. Turning it on or off,
volume ×7 up and ×7 down, the mode key and its amplifier on/off key produced **no** AVC-LAN
frame (2026-10-07, marked capture). The display's audio screen (`5E`) has no audio source to
talk to. The aftermarket unit's own internals (its MCU, steering-wheel key interface, CAN box)
are **not** AVC-LAN and are out of scope here.

## 7.3 Things that stay inside one unit

| Action | On the bus? | Verified |
|---|---|---|
| Physical (dashboard) climate temperature buttons | no key frame; only the `E0 5D F5` status changes | USER, 2026-10-07 |
| Physical rear-window heater button | no key frame; only `E0 5D F3` b4 bit 0x08 changes | USER, 2026-10-07 |
| Display keys that select its own screens (INFO, CLIMATE, …) | no key frame; only the `12 01 60 SS` screen broadcast (and `43 02 00` if the nav owned the screen) | DECODE + USER |
| Touches on the display's own screens | no coordinates; only resulting commands (e.g. climate keys to `1C6`) | DECODE |
| MENU / DEST / MAP with no nav registered | nothing at all | DECODE, 2026-10-07 unplug test |
| Fog lights, turn indicators, low/high beam change | nothing (only lights on/off → `01 01 5B 40` / `5A 80`) | USER, 2026-10-07 |

## 7.4 Vehicle data that is not on AVC-LAN here

- **Vehicle speed** and **engine rpm**: not found. They are on CAN.
- **Energy-flow arrows** *are* on AVC-LAN (`E4 5F B9`). A CAN ID that secondary sources
  describe as an "energy flow" frame (0x3B6) was not present on the CAN segment we tapped.
- **Cabin (inside) temperature**: not found on AVC-LAN. Only the outside temperature and the
  set temperature are present.
- Secondary sources describe AVC-LAN ID 0x130 as climate data ("A/C amplifier"). On this car
  no unit with that address transmitted; all climate data comes from `1C6`
  (logical `E0`).
