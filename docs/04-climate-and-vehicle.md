# 4. Gateway (1C6) frames: climate, outside temperature, energy monitor, trip

All these frames come from the gateway ECU `1C6`, mostly addressed to the display `110`.
Verification tags: **USER** = the operator confirmed it on the car's own display or by acting
on the control; **CAN** = correlated with CAN data from the same seconds; **TX** = we sent the
frame and the car reacted as described; **DECODE** = structure/period only; **INF** =
inference (unverified).

Byte numbering: `b0` is the first data byte (`00` in unicasts).

## 4.1 Outside temperature

`1C6→110 00 E0 5D F7 TT`, every 1 s, always (also without a nav).

**Outside temperature (°C) = TT − 48.** For example `44` = 20 °C and `3E` = 14 °C. USER:
confirmed at 20, 21 and 22 °C against the car's own readout (2026-10-07). The 2026-10-14
captures decode to 13–15 °C, which is plausible for that afternoon but was not checked against
the readout.

The same value is returned as `00 E0 5D F8 TT` when the display subscribes (4.6).

## 4.2 Climate status

`1C6→110 00 E0 5D F3 b4 b5 b6 b7 b8 b9`, every 5 s and immediately after any change.

| Byte / bit | Meaning | Verified |
|---|---|---|
| b4 bit 0x80 | AUTO | USER, 2026-10-07 |
| b4 bit 0x40 | fresh air (outside air intake) | USER |
| b4 bit 0x20 | recirculation | USER |
| b4 bit 0x10 | front windshield defroster | USER, 2026-10-14 |
| b4 bit 0x08 | rear window heater | USER, 2026-10-07 (drive) |
| b4 bit 0x02 | A/C compressor on | USER |
| b4 bit 0x01 | "face only" vent mode (together with b5 = `00`); AUTO states also show it | USER |
| b5 | vent mode: `80` face + foot, `40` foot, `20` windscreen + foot, `00` face (with b4 bit 0x01) | USER |
| b6 bit 0x04 | button-accepted pulse: set in the one status frame sent right after a key press | DECODE |
| b9 bits 7–5 (b9 >> 5) | fan speed 1–7 (`20` … `E0`); `00` = climate system OFF | USER, 2026-10-07 (stepped 1 → 7) |
| b7, b8 | always `00` in our captures | DECODE |

Typical values: `C3 00 00 00 00 20` = AUTO, fresh air, face, fan 1. `23 00 00 00 00 20` =
recirculation, face, fan 1. `41 00 00 00 00 00` = system OFF. `52 00 00 00 00 40` = defrost
with A/C, fan 2.

## 4.3 Climate set temperature

`1C6→110 00 E0 5D F5 NN 38`, every 5 s and on change.

**Set temperature (°C) = 15.5 + 0.5 × NN.** `07` = 19.0, `0A` = 20.5, `0B` = 21.0, `0F` =
23.0. **NN = `39` while the climate system is OFF.** USER: 19.0 → 20.5 → 19.0 checked step
by step (2026-10-07), and 18.5 → 20.0 with three remote presses (2026-10-14). The trailing
`38` never changed.

## 4.4 Climate keys (display → climate control)

`110→1C6 00 25 E0 84 k4 k5 k6 k7 k8 k9`. The display sends the key code when an on-screen
key is touched, then sends the release (all six bytes `00`).

| Key | k4 k5 k6 k7 k8 k9 | Verified |
|---|---|---|
| temperature + 0.5 °C | `80 00 00 00 00 00` | USER + TX, 2026-10-14 |
| temperature − 0.5 °C | `40 00 00 00 00 00` | USER + TX, 2026-10-14 |
| AUTO | `08 00 00 00 00 00` | USER + TX |
| OFF | `04 00 00 00 00 00` | USER, 2026-10-14 (F3 → `41 00…`, F5 → `39`; AUTO restores the previous set temperature) |
| recirculation | `02 00 00 00 00 00` | USER + TX |
| front windshield defrost (toggle) | `01 00 00 00 00 00` | USER, 2026-10-14 |
| rear window heater (toggle) | `00 80 00 00 00 00` | USER, 2026-10-14 |
| A/C on/off (toggle) | `00 20 00 00 00 00` | USER + TX |
| face | `00 08 00 00 00 00` | USER |
| face + foot | `00 04 00 00 00 00` | USER |
| foot | `00 02 00 00 00 00` | USER |
| windscreen + foot | `00 01 00 00 00 00` | USER |
| fan 1 | `00 00 80 00 00 00` | USER |
| fan 2 | `00 00 40 00 00 00` | USER |
| fan 3 | `00 00 20 00 00 00` | USER |
| fan 4 | `00 00 10 00 00 00` | USER |
| fan 5 | `00 00 00 00 08 00` | USER + TX ("fan started blowing at 5th stage") |
| fan 6 | `00 00 00 00 04 00` | USER |
| fan 7 | `00 00 08 00 00 00` | USER + TX |

The fan bits are not monotonic (fans 5 and 6 sit in k8), but the table is as captured.

**Sending these frames remotely works** (TX, 2026-10-14). Send master `110` → slave `1C6`,
control `F`, press frame, then the release ≈ 100–150 ms later. Each press/release pair is one
step. Holding (≈ 0.6 s before the release) auto-repeats, just as a held finger does. Each
change is confirmed by the next `E0 5D F3`/`F5` status frame. The **physical** temperature
and rear-heater buttons on the dashboard send **no** frame. Only the status frames change.

Example: [`examples/04_climate_onscreen_buttons.csv`](../examples/04_climate_onscreen_buttons.csv).

## 4.5 Climate data subscriptions

The display (logical `5D`) and the nav (logical `85`) each subscribe to the climate controller
`E0`. The reply opcode is the request + 0x10:

| Request | Reply | Content |
|---|---|---|
| `xx→1C6 00 5D/85 E0 E0` | `00 E0 5D/85 F0 00 71` | unknown constant |
| `… E0 E4` | `… F4 <same 6 bytes as F3>` | climate status |
| `… E0 E6` | `… F6 <same 2 bytes as F5>` | set temperature |
| `… E0 E8` (display only) | `… F8 TT` | outside temperature |

Verified: DECODE, 2026-10-07 and 2026-10-14 (genuine nav and emulator, which receives
identical replies).

## 4.6 Energy monitor arrows

`1C6→110 00 E4 5F B9 F1 F2 00`, every ≈ 0.5 s. The display draws an MG (motor/generator)
node. Charging is always drawn engine → MG → battery; there is no direct engine → battery
arrow. One bit per arrow:

| Byte | Bit | Arrow | Verified |
|---|---|---|---|
| F1 | 0x40 | engine → wheels | USER + CAN, 2026-10-14 drive |
| F1 | 0x08 | engine → MG (generating) | USER + CAN |
| F1 | 0x20, 0x04 | link flags, always together with the bits above | DECODE |
| F2 | 0x80 | wheels → MG (regeneration) | USER + CAN |
| F2 | 0x40 | MG → wheels (motor driving) | USER + CAN |
| F2 | 0x10 | battery → MG (discharging) | USER + CAN |
| F2 | 0x08 | MG → battery (charging: generator or regeneration) | USER + CAN |
| F2 | 0x20, 0x04 | link flags (MG–wheels, MG–battery) | DECODE |

States seen, with CAN averages over the same seconds (rpm = CAN 0x3C8 bytes 2–3 ÷ 8; speed
0x0B4; throttle 0x244; battery current 0x03B, negative = charging):

| F1 F2 | Arrows on the display (user) | rpm | km/h | throttle | battery A |
|---|---|---|---|---|---|
| `00 00` | none | 0 | 0 | 0 | ≈ 0 |
| `0C 0C` | engine→MG, MG→battery (idle charging, parked) | 1280 | 0 | 0 | −14 |
| `6C 0C` | engine→wheels, engine→MG, MG→battery (steady cruise) | 1540 | 35 | 33 | −18 |
| `6C 6C` | engine→wheels, engine→MG, MG→wheels, MG→battery | 1830 | 28 | 60 | −16 |
| `6C 60` | engine→wheels, engine→MG, MG→wheels | 1980 | 30 | 71 | ≈ 0 |
| `6C 74` | engine→wheels, engine→MG, battery→MG, MG→wheels | 1820 | 21 | 82 | +18…+61 |
| `00 74` | battery→MG, MG→wheels (EV driving) | 0 | 8 | 21 | +8 |
| `00 AC` | wheels→MG, MG→battery (regeneration) | 250 | 25 | brake | −20…−73 |

**Engine running ⇔ F1 ≠ 00** (USER + CAN). Against CAN rpm over 9 engine starts and 9 stops
(2026-10-07), F1 turns on within −0.28…+0.06 s of the engine start. F1 turns off when the
engine stops delivering power; the rpm then spins down to 0 within 1.1–2.8 s. All ≈ 20 parked
engine runs on 2026-10-14 were `0C 0C` throughout (engine charging the battery only).

> A reading published in an earlier draft (F2 0x40 = "battery →", 0x08 = "wheels →") was
> wrong. The table above superseded it after the 2026-10-14 drive with the user checking each
> arrow.

Example: [`examples/05_energy_monitor_drive.csv`](../examples/05_energy_monitor_drive.csv).

## 4.7 Battery bars, EV mode, shift position

| Frame | Field | Meaning | Verified |
|---|---|---|---|
| `1C6→110 00 E4 5F B8 00 00 XX YY 00` (1 s) | `(XX & 0x07) + 1` | **battery level in bars** shown on the display | USER, 2026-10-07 drive (4 → 3 → 4 → 5) |
| | XX bit 0x08 | toggles every few seconds; unknown | DECODE |
| | XX bit 0x80 | always set; unknown | DECODE |
| | YY bit 0x40 | **EV mode active** | USER, 2026-10-07 (EV button on/off ×3) |
| | YY bit 0x80 | **EV mode cancelled** notice (≈ 3.5 s, e.g. throttle pressed too far) | USER, 2026-10-07 |
| `1C6→110 00 E4 5F B4 SS` (1 s) | SS | shift-related: `84` parked (P), `0C` driving, `04` briefly when moving through R/N; `80 82 86` rare | INF (drive observations, not confirmed against the shift lever) |
| `1C6→1FF E4 31 B6 GG 00 00` (B, 1 s) | GG | `80` whenever B4 = `84`; `10`, `40`, `20`, `00` while B4 = `0C`. Hypothesis: one-hot P/R/N/D (`80/40/20/10`) | INF (correlation only) |
| `1C6→110 00 E5 5F B5 0C 01` (1 s) | | `04 01` in a few frames; possibly shift-related | INF |

## 4.8 Engine / power-like values

| Frame | Observation | Status |
|---|---|---|
| `1C6→110 00 E4 5F 97 HH LL` (≈ 0.8–1 Hz, only while the engine runs or shortly after) | 16-bit big-endian. ≈ 0x2A3–0x2F9 (675–761) parked, ≈ 950–1180 while driving with OBD rpm 1300–2260. **Not rpm.** Ramps to 0 a few seconds after the engine stops on some runs and freezes on others | INF: engine-load or power-like |
| `1C6→110 00 E5 5F D8 HH LL 40` (≈ 0.5 s) | signed 16-bit: 0 in EV, `FF FE` (−2) while the engine idles parked, +40…+600 when the engine pulls. Follows the engine flag with ≈ 1.5 s lag | INF: engine power / torque-like |
| `1C6→110 00 E4 5F 96 TT` (1 s) | slowly rising: `4D` at the first cold start of a day, `70` minutes later, `8C`–`A6` while driving | INF (see [08](08-open-questions.md)) |
| `1C6→110 00 E5 5F DC HH LL 80` (≈ 8 s, on change) | rose `2F 94` → `2F 99` during a short drive only; constant while parked | INF: distance counter, 0.1 km steps? |
| `1C6→110 00 E5 5F DB 00 NN 40` (10 s) | NN `47`–`4A` | unknown |
| `1C6→110 00 E4 00 95 00`, `00 E5 5F B7 00 00 00 00 00` (1 s) | constant in every capture | unknown |
| `1C6→110 00 25 32 84 00 00 00` (5 s) | `40 00 00` / `00 00 04` once each while the set temperature was being changed | unknown key/status frame to display function 32 |

**No vehicle speed and no engine rpm** were found on AVC-LAN in this car. For those, use CAN
(speed 0x0B4, rpm in 0x3C8, ICE flag 0x038 on the CAN bus tapped for the correlation).
