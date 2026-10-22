# Example captures

Short excerpts of real bus traffic from the author's car. Each is a plain CSV file with one
decoded AVC-LAN frame per line.

## Format

```
t_ms,type,master,slave,ctrl,ack,origin,data
0,B,110,FFF,F,,car,12 01 00
5,U,178,110,F,ok,car,00 01 12 10 58 24 85
```

| Column | Meaning |
|---|---|
| `t_ms` | milliseconds since the first line of the file. The time is when the receiver finished decoding the frame (1 ms resolution) |
| `type` | `B` = broadcast (broadcast bit 0), `U` = unicast |
| `master` | 12-bit sender address, hex |
| `slave` | 12-bit receiver address, hex (`1FF`/`FFF` for broadcasts) |
| `ctrl` | 4-bit control field, hex (always `F` on this car) |
| `ack` | unicasts only: `ok` = every ACK slot was acknowledged, `NAK` = at least one slot was not; empty for broadcasts |
| `origin` | `car` = sent by a unit of the car; `emulator` = sent by the author's nav emulator (address `178`) and received back from the bus |
| `data` | data bytes, hex, space separated, in bus order (the length field is implicit) |

Frames with parity errors are not included; the receiver drops them.

## Files

| File | Date | Content |
|---|---|---|
| `01_rollcall_real_nav_cold_start.csv` | 2026-10-14 | Cold start with the **genuine** nav. Roll call with truncated answers while the nav is still booting, display setup with defaults, then (at ≈ 19.6 s) the nav's late announcement `01 12 13 58 24 85`, the full re-setup dialogue and the language reply `B7 02`. Unfiltered, 21 s |
| `02_screen_switch_emulated_nav.csv` | 2026-10-14 | DEST pressed twice with the emulated nav: `50` request → `42` offer → `52` + `58 31 F1 02 00` → screen `58`; leaving the nav screen (`43` → `53`), once to climate and once to info. Unfiltered, 5 s |
| `03_touch_strokes.csv` | 2026-10-14 | Touch frames only (`110→178 00 21 24 78 …`): taps near the four corners and edges, then a left-to-right drag. Filtered |
| `04_climate_onscreen_buttons.csv` | 2026-10-14 | On-screen climate keys (temp + ×2, temp − ×2, rear heater on/off) with the resulting `E0 5D F3`/`F5`/`F7` frames. Filtered to `110→1C6` and `1C6→110 … E0 …` |
| `05_energy_monitor_drive.csv` | 2026-10-14 | 2 minutes of driving: energy-monitor arrows `E4 5F B9`, battery/EV `E4 5F B8`, shift `E4 5F B4` and outside temperature `E0 5D F7`. Seven different arrow states. Filtered |
| `06_rollcall_amp_powered.csv` | 2026-10-19 | Cold-start roll call with the amplifier switched on: only `178` (emulator) and `1C6` answer. Full emulated setup. Unfiltered, 2.5 s |

Filtered files keep the original timing of the frames they contain; frames that do not match
the filter are simply left out.
