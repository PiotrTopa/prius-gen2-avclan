# 8. Open questions, guesses and differences from other Toyotas

**Everything in sections 8.1 and 8.2 is unverified.** These are guesses, labelled so that
nobody mistakes them for facts. Contributions that confirm or refute them are welcome.

## 8.1 Unknown or partly understood frames

| Frame | What we know | Guess (unverified) |
|---|---|---|
| `1C6→110 00 E4 5F 96 TT` (1 s) | rises slowly: `4D` at a day's first cold start, `70` minutes later, `8C`–`A6` while driving | **coolant temperature in 0.5 °C steps (TT / 2 °C)**: 38 → 56 → 70–83 °C would fit a warming engine. `TT − 40` gives 126 °C, so it is not the OBD scale. Needs a check against OBD PID 0x05 |
| `1C6→110 00 E4 5F 97 HH LL` | 16-bit, present only around engine runs, not rpm | engine load / power request |
| `1C6→110 00 E5 5F D8 HH LL 40` | signed 16-bit, 0 in EV, small negative idling, up to +600 under engine load | engine output power or torque |
| `1C6→110 00 E5 5F DC HH LL 80` | increments only while driving | distance / trip counter (0.1 km?) |
| `1C6→110 00 E5 5F DB 00 NN 40` (10 s) | NN `47`–`4A`, changes slowly | average consumption or range for the trip screen |
| `1C6→110 00 E4 5F B4 SS` | `84` parked, `0C` driving, `04` transitional | shift lever / READY state |
| `1C6→1FF E4 31 B6 GG 00 00` | `80` when B4 = `84`; `10/40/20/00` otherwise | one-hot P/R/N/D/B |
| `1C6→110 00 E4 5F B8 … XX …` bit 0x08 | toggles every few seconds | battery gauge animation phase |
| `1C6→110 00 E4 5F BA nn` (60 s) | nn `00`–`07` | — |
| `1C6→110 00 E4 00 95 00`, `00 E5 5F B7 00 00 00 00 00` | constant | fields that other trims or markets use |
| `1C6→110 00 25 32 84 00 00 00` (5 s) | rare `40 00 00`, `00 00 04` | — |
| `1C6→FFF E5 01 9C 57 42 4C 41 45 4E` | ASCII `WBLAEN`, every 60 s after `110→1C6 00 01 E5 8C` | a unit or variant identifier |
| `1C6→110 00 E0 5D F0 00 71` | reply to the climate subscription `E0` | capability flags of the climate control |
| `110→FFF 01 01 5F xx` (5 s) | xx `09` mostly, `0F`, `0B`, `01` | display brightness / dimmer level |
| `110→FFF 12 01 60 SS MM 00 05` byte MM | `01` for nav, `05` for the display's own screens | "external" vs "internal" source |
| ping reply `00 01 12 30 XX YY` from 1C6 | YY = `00` on 2026-10-07, `FF` from 2026-10-14 on | a state flag of the gateway |
| nav `9F` identification payload | two different payloads on two days | version/checksum, partly per boot |
| nav time reply `9E 00 PP 01 HH MM SS FF` | PP `03` or `01`; clock origin unclear | PP = time source or validity |
| nav device tables (`27 58 40 64 62 61 55 6E 6D`, `34 A2 58 43 63 65 44 45 E0`) and the display's per-unit queries (`17 80 11 03 11 07`, …) | replayed verbatim, accepted | (type, logical) pairs; the meaning of the pairs is unknown |
| nav language list | the "Language" soft key (`00 25 58 80 40 00 00`) gets an ACK, then the nav must draw a page | the nav draws its own page on screen 58 (video), so there may be no bus-level list at all |

## 8.2 Electrical

- Whether other harness locations (head-unit connector, gateway connector) show the same
  idle offset of ≈ +50 mV. A receiver with a ≈ 100 mV threshold has little margin if some
  location idles nearer +100 mV.
- How many units terminate the bus, and with what impedance. Not measured.

## 8.3 Differences from published prior art (other Toyota models)

| Topic | Prior art (mostly Corolla / other models) | This Prius (NHW20, nav + JBL) |
|---|---|---|
| Bit timing | "0" ≈ 33 µs high / 7 µs low, "1" ≈ 20 µs / 20 µs; bit ≈ 39–40 µs | **agrees**: 32–34 / 20 µs dominant, 39 µs slot |
| Frame layout (broadcast bit, master, slave, control, length, data; leading `00` in unicasts) | as listed | **agrees**. The one exception is the broadcast `00 01 07` |
| `110` EMV, `178` NAVI, `1C6` G/W | as listed | **agrees** |
| Head unit `190`/`160`, amplifier `440`/`480` present | typical | **absent** here (factory audio removed; amplifier silent) |
| `110→178 00 21 24 78 xx yy xx yy` touch | as listed | **agrees**. Added: origin bottom-left, ranges and calibration |
| `12 01 46` "any device in use" | sent by the head unit `160` | **agrees** in content, but here the display `110` sends it every 5 s |
| `12 01 00` / `12 01 01` | named "back from LAN check" / "LAN restart" | here they behave as **roll call** and **device-table request** (units answer with their logical IDs) |
| Logical `85` | voice control | here only a nav-side climate subscriber |
| Logical `E4` | not listed | energy/drive data source in 1C6 (new) |
| Screen broadcast `12 01 60 SS` with SS = drawing logical | not described | new |
| Climate frames `E0 5D F3/F5/F7`, climate keys `25 E0 84` | not described | new (this document) |
| Energy-monitor bit map `E4 5F B9` | not described | new (this document) |
| Screen request/grant/release `50/42/52/43/53`, `58 31 F1` | not described | new (this document) |
| Language byte `58 56 B7 LL` | not described | new (this document) |
