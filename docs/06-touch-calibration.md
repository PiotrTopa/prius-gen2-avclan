# 6. Touch coordinates and key codes

## 6.1 Touch frame

`110→178 00 21 24 78 X Y X Y`

- Sent only while the display shows the **nav screen (58)** and a nav is registered
  ([02 §2.3](02-devices.md#23-startup-roll-call-cold-bus)).
- `X Y` is one byte each, and the pair is sent twice (bytes 6–7 always equal bytes 4–5 in
  582 frames).
- ≈ 10–15 frames/s while the finger is down; positions jitter by 1–2 counts on a held finger.
- `00 00 00 00` = finger lifted (one frame).

Verified: DECODE + USER, 2026-10-07 (four corners) and 2026-10-14 (12 calibration strokes).

## 6.2 Raw ranges (measured 2026-10-14, user touching the panel edges)

| Touch | X | Y |
|---|---|---|
| top-left corner | 4–13 | 245–255 |
| top-right corner | 246–249 | 249–255 |
| bottom-right corner | 244–246 | 9–19 |
| bottom-left corner | 5–9 | 9–15 |
| drag left → right, mid-height | 4 → 248 | ≈ 135 |
| drag top → bottom, mid-width | ≈ 128 | 253 → 13 |

**X grows left → right and Y grows bottom → top: the origin is the bottom-left corner.**
The usable range is about X 4…249, Y 9…255.

## 6.3 Mapping to the 480 × 240 picture

The nav screen's native video is 480 × 240 pixels. A linear fit to the strokes:

```
px = (X − 4)   × 480 / 245      ≈ 1.96 px per count
py = (255 − Y) × 240 / 246      ≈ 0.98 px per count
clamp px to 0…479, py to 0…239
```

Check (the recorded strokes replayed through this mapping, 2026-10-15): the four corner strokes land within ≤ 25 px of the
picture corners, and a tap at `X=0x7F, Y=0x2F` maps to (240, 203). The X resolution
(≈ 2 px per count) limits how small touch targets can be. Use targets of at least ≈ 20 × 20 px.

Example strokes: [`examples/03_touch_strokes.csv`](../examples/03_touch_strokes.csv). It has
taps near the four corners and edges, then a horizontal drag through the middle (X 04 → F9 at Y ≈ 83–8F).

## 6.4 Key codes (summary)

| Source | Frame | Codes |
|---|---|---|
| Nav hardware keys | `110→178 00 25 58 84 KK 00` | `01` MENU, `04` DEST, `02` MAP, `00` release |
| Info-page soft keys owned by the nav | `110→178 00 25 58 80 KK 00 00` | `01` Maintenance, `08` Calendar, `40` Language |
| Climate on-screen keys | `110→1C6 00 25 E0 84 k4…k9` | see [04 §4.4](04-climate-and-vehicle.md#44-climate-keys-display--climate-control) |

The display's own screen-select keys produce no key frames on this car's AVC-LAN
([07](07-what-is-not-on-the-bus.md)). Steering-wheel audio keys were not tested against
AVC-LAN.
