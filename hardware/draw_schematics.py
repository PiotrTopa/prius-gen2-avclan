#!/usr/bin/env python3
"""AVC-LAN (Toyota IEBus) transceiver for the RP2040-Zero -- schematic drawings.

Generates (SVG + PNG, next to this script):
  avclan_transceiver_rx.*    comparator receiver stage, as built (measured in the car 2026-10-14)
  avclan_transceiver_tx.*    discrete push-pull driver stage
  avclan_transceiver_full.*  both stages + H1 + RP2040-Zero + notes

Run:  .venv-draw/bin/python draw_schematics.py
Needs: schemdraw (0.23), matplotlib.  See VALUES.md for the source of every value.
"""
from pathlib import Path

import schemdraw
import schemdraw.elements as elm

OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- values ---
# RX (measured on the built board, car, 2026-10-14) -- authoritative
R1_VAL = "10 kΩ"        # H1 left (T, WHITE, Data+) -> LM339 pin 7 (IN+); measured 9.62 k
R2_VAL = "10 kΩ"        # H1 right (BROWN, Data-) -> LM339 pin 6 (IN-); measured 9.87 k
R3_VAL = "4.7 kΩ"       # LM339 pin 1 (OUT) pull-up to 3V3 -> GP0
RBIAS_VAL = "220 kΩ"    # LM339 pin 3 (5 V) -> pin 6 (IN-); moved from GND to 5 V on 2026-10-14
C1_VAL = "100 nF"       # LM339 VCC (pin 3) decoupling
R2M_VAL = "2 MΩ"        # 3V3 -> pin 6 (IN-): second bias path, fitted by design (user-confirmed 2026-10-22)
U2_NAME = "LM339 (unit 2)"

# TX -- as built (user-confirmed 2026-10-22): the upgraded part set.
TX_SET = "as built (user-confirmed 2026-10-22)"
R4_VAL = "2.2 kΩ"       # GP1 -> Q1 base
R5_VAL = "2.2 kΩ"       # Q1 collector -> Q2 base
R6_VAL = "1 kΩ"         # Q2 base -> 5 V (holds Q2 off)
R7_VAL = "68 Ω"         # D1 cathode -> Data+
R8_VAL = "68 Ω"         # Data- -> D2 anode
D_VAL = "BAT54"         # D1, D2
Q1_NAME = "BC547"       # NPN (netlist MPN 2N3904S, value field BC547)
Q2_NAME = "BC327"       # PNP
RBLEED_VAL = "12 kΩ"    # Q2 collector (D1 anode) -> GND, added 2026-10-13

FONT = 11
SMALL = 9.5

# ---------------------------------------------------------------- helpers --


def text(d, xy, s, size=FONT, halign="center", valign="center", color="black"):
    d.add(elm.Label().at(xy).label(s, fontsize=size, halign=halign, valign=valign, color=color))


def wire(d, *pts):
    for a, b in zip(pts, pts[1:]):
        d.add(elm.Line().at(a).to(b))


def dot(d, xy, open_=False):
    d.add(elm.Dot(open=open_).at(xy))


def box(d, x0, y0, x1, y1, lw=1.6):
    wire(d, (x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))


def supply(d, xy, name):
    d.add(elm.Vdd().at(xy).label(name, fontsize=FONT))


def gnd(d, xy):
    d.add(elm.Ground().at(xy))


def terminal(d, xy, s, side="left", size=FONT):
    """Open terminal (net end) with its name on `side`."""
    dot(d, xy, open_=True)
    dx = -0.3 if side == "left" else 0.3
    text(d, (xy[0] + dx, xy[1]), s, size=size, halign="right" if side == "left" else "left")


# --------------------------------------------------------------- RX stage --
# Bus side enters at x = XM (Data-) / XP (Data+); output leaves at x = XOUT.


def draw_rx(d, oy, xm, xp, xout):
    """Comparator receiver. oy = y of the comparator output line."""
    y_m = oy + 0.62          # IN- (pin 6) line, Data-
    y_p = oy - 0.62          # IN+ (pin 7) line, Data+
    x_op = 11.0
    op = d.add(elm.Opamp(leads=False).right().anchor("center").at((x_op + 1.71, oy)))
    # inputs
    n6 = (10.2, y_m)
    wire(d, (xm, y_m), (6.9, y_m))
    d.add(elm.Resistor().at((6.9, y_m)).to((9.3, y_m))
          .label(f"R2  {R2_VAL}", loc="top", fontsize=FONT))
    wire(d, (9.3, y_m), op.in1)
    dot(d, n6)
    wire(d, (xp, y_p), (6.9, y_p))
    d.add(elm.Resistor().at((6.9, y_p)).to((9.3, y_p))
          .label(f"R1  {R1_VAL}", loc="bottom", fontsize=FONT))
    wire(d, (9.3, y_p), op.in2)
    text(d, (op.in1[0] - 0.25, y_m + 0.3), "6", size=SMALL)
    text(d, (op.in2[0] - 0.25, y_p - 0.3), "7", size=SMALL)
    # 5 V rail of the comparator: pin 3, bias resistor, decoupling
    y5 = oy + 4.2
    d.add(elm.Resistor().up().at(n6).to((n6[0], y5))
          .label(f"Rbias\n{RBIAS_VAL}", loc="bottom", fontsize=FONT))
    # second bias path: 2 MΩ from 3V3 into pin 6 (deliberate, user-confirmed)
    n2m = (9.65, y_m)
    dot(d, n2m)
    d.add(elm.Resistor().up().at(n2m).to((n2m[0], y_m + 2.3))
          .label(f"R2M\n{R2M_VAL}", loc="top", fontsize=FONT))
    supply(d, (n2m[0], y_m + 2.3), "3V3")
    vd = op.vd
    wire(d, vd, (vd[0], y5))
    text(d, (vd[0] + 0.3, vd[1] + 0.45), "3", size=SMALL)
    wire(d, (7.6, y5), (vd[0], y5))
    for x in (n6[0], vd[0]):
        dot(d, (x, y5))
    supply(d, (11.3, y5), "+5 V")
    dot(d, (11.3, y5))
    d.add(elm.Capacitor().down().at((7.6, y5)).to((7.6, y5 - 1.6))
          .label(f"C1\n{C1_VAL}", loc="bottom", fontsize=FONT))
    gnd(d, (7.6, y5 - 1.6))
    # GND pin 12
    vs = op.vs
    wire(d, vs, (vs[0], vs[1] - 0.9))
    gnd(d, (vs[0], vs[1] - 0.9))
    text(d, (vs[0] - 0.35, vs[1] - 0.4), "12", size=SMALL)
    # output, open collector, pull-up to 3V3
    out = op.out
    text(d, (out[0] + 0.25, out[1] + 0.3), "1", size=SMALL)
    text(d, (vs[0] + 0.45, oy - 1.25), f"U2  {U2_NAME}", size=FONT, halign="left")
    text(d, (vs[0] + 0.45, oy - 1.75), "open-collector output", size=SMALL, color="#444", halign="left")
    nr3 = (15.6, oy)
    wire(d, out, (xout, oy))
    dot(d, nr3)
    d.add(elm.Resistor().up().at(nr3).to((nr3[0], oy + 2.6))
          .label(f"R3\n{R3_VAL}", loc="bottom", fontsize=FONT))
    supply(d, (nr3[0], oy + 2.6), "3V3")
    return op


# --------------------------------------------------------------- TX stage --


def draw_tx(d, oy, xm, xp, xin):
    """Push-pull driver.  oy = y of the 5 V rail; GP1 enters from x = xin."""
    y5 = oy
    xr = 15.0                       # R5/R6 column = Q2 base node
    # Q2 PNP, base on the right
    q2 = d.add(elm.BjtPnp(circle=True).right().reverse().anchor("base").at((14.0, oy - 2.0)))
    text(d, (q2.center[0] - 0.75, q2.center[1]), f"Q2\n{Q2_NAME}\nPNP", halign="right")
    wire(d, q2.emitter, (q2.emitter[0], y5))
    wire(d, q2.base, (xr, q2.base[1]))
    nb2 = (xr, q2.base[1])
    dot(d, nb2)
    d.add(elm.Resistor().up().at(nb2).to((xr, y5))
          .label(f"R6  {R6_VAL}", loc="bottom", fontsize=FONT))
    wire(d, (q2.emitter[0], y5), (xr, y5))
    supply(d, (14.1, y5), "+5 V")
    dot(d, (14.1, y5))
    # Q2 collector node -> D1 -> R7 -> Data+
    yc2 = oy - 3.1
    nc2 = (q2.collector[0], yc2)
    wire(d, q2.collector, nc2)
    dot(d, nc2)
    d.add(elm.Diode().left().at((12.2, yc2)).to((10.2, yc2))
          .label(f"D1  {D_VAL}", loc="top", fontsize=FONT))
    wire(d, nc2, (12.2, yc2))
    d.add(elm.Resistor().left().at((9.6, yc2)).to((7.2, yc2))
          .label(f"R7  {R7_VAL}", loc="top", fontsize=FONT))
    wire(d, (10.2, yc2), (9.6, yc2))
    wire(d, (7.2, yc2), (xp, yc2))
    text(d, (11.7, yc2 - 0.45), "A", size=SMALL - 1, color="#444")
    text(d, (10.7, yc2 - 0.45), "K", size=SMALL - 1, color="#444")
    # bleeder from Q2 collector to GND
    d.add(elm.Resistor().down().at(nc2).to((nc2[0], yc2 - 1.9))
          .label(f"Rbleed\n{RBLEED_VAL}", loc="top", fontsize=FONT))
    gnd(d, (nc2[0], yc2 - 1.9))
    # R5 from Q2 base node down to Q1 collector node
    yd2 = oy - 6.4
    nc1 = (xr, yd2)
    d.add(elm.Resistor().down().at(nb2).to((xr, nb2[1] - 2.4))
          .label(f"R5  {R5_VAL}", loc="bottom", fontsize=FONT))
    wire(d, (xr, nb2[1] - 2.4), nc1)
    dot(d, nc1)
    # Data- -> R8 -> D2 (anode left, CATHODE at Q1 collector) -> Q1 collector
    wire(d, (xm, yd2), (7.2, yd2))
    d.add(elm.Resistor().right().at((7.2, yd2)).to((9.6, yd2))
          .label(f"R8  {R8_VAL}", loc="bottom", fontsize=FONT))
    wire(d, (9.6, yd2), (10.2, yd2))
    d.add(elm.Diode().right().at((10.2, yd2)).to((12.2, yd2))
          .label(f"D2  {D_VAL}", loc="bottom", fontsize=FONT))
    text(d, (10.7, yd2 + 0.45), "A", size=SMALL - 1, color="#444")
    text(d, (11.7, yd2 + 0.45), "K", size=SMALL - 1, color="#444")
    wire(d, (12.2, yd2), nc1)
    # Q1 NPN, base on the right, collector up to nc1
    q1 = d.add(elm.BjtNpn(circle=True).right().reverse().anchor("collector").at((xr, yd2 - 1.3)))
    text(d, (q1.center[0] - 0.75, q1.center[1]), f"Q1\n{Q1_NAME}\nNPN", halign="right")
    wire(d, nc1, q1.collector)
    wire(d, q1.emitter, (q1.emitter[0], q1.emitter[1] - 0.6))
    gnd(d, (q1.emitter[0], q1.emitter[1] - 0.6))
    yb1 = q1.base[1]
    d.add(elm.Resistor().right().at(q1.base).to((q1.base[0] + 2.4, yb1))
          .label(f"R4  {R4_VAL}", loc="top", fontsize=FONT))
    wire(d, (q1.base[0] + 2.4, yb1), (xin, yb1))
    return yc2, yd2, yb1


# ---------------------------------------------------------------- sheets ---

def finish(d, name):
    for ext in ("svg", "png"):
        d.save(str(OUT / f"{name}.{ext}"), dpi=200) if ext == "png" else d.save(str(OUT / f"{name}.{ext}"))


def sheet_rx():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=FONT, unit=2.4, lw=1.4, bgcolor="white")
        oy = 0.0
        draw_rx(d, oy, xm=5.0, xp=5.0, xout=18.0)
        terminal(d, (5.0, oy + 0.62), "Data−   (H1 right, car BROWN)")
        terminal(d, (5.0, oy - 0.62), "Data+   (H1 left \"T\", car WHITE)")
        terminal(d, (18.0, oy), "GP0  (RP2040 AVC RX)", side="right")
        text(d, (11.0, oy + 5.6), "AVC-LAN receiver — as built, measured in the car 2026-10-14", size=FONT + 2)
        text(d, (11.0, oy - 3.0), "No feedback (hysteresis) resistor.  Rbias pulls pin 6 ≈ +105 mV above Data− at idle"
             " → OUT idles LOW;", size=SMALL)
        text(d, (11.0, oy - 3.5), "dominant (Data+ above Data−) → OUT HIGH → firmware  pol hi.   "
             "LM339 VCC = pin 3 = the RP2040's 5 V; GND = pin 12.", size=SMALL)
        text(d, (11.0, oy - 4.0), "R3 pulls up to 3V3 (not 5 V): level shift for GP0.  "
             "H1 has no GND pin; bus ground = board GND.", size=SMALL)
        finish(d, "avclan_transceiver_rx")


def sheet_tx():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=FONT, unit=2.4, lw=1.4, bgcolor="white")
        oy = 0.0
        yc2, yd2, yb1 = draw_tx(d, oy, xm=5.0, xp=5.0, xin=19.5)
        terminal(d, (5.0, yc2), "Data+   (H1 left \"T\", car WHITE)")
        terminal(d, (5.0, yd2), "Data−   (H1 right, car BROWN)")
        terminal(d, (19.5, yb1), "GP1  (RP2040 AVC TX)", side="right")
        text(d, (12.0, oy + 1.6), "AVC-LAN driver — push-pull dominant, high-Z recessive", size=FONT + 2)
        text(d, (12.0, oy + 1.0), f"TX values = {TX_SET}; earlier netlist values: see VALUES.md",
             size=SMALL, color="#a00")
        y = yb1 - 2.4
        text(d, (12.0, y), "GP1 HIGH = dominant: Q1 sinks Data− (R8, D2); Q1 pulls Q2's base low via R5, "
             "Q2 sources Data+ from 5 V (D1, R7).", size=SMALL)
        text(d, (12.0, y - 0.5), "GP1 LOW (idle) = recessive: Q1 off, R6 holds Q2 off, D1/D2 block back-feed "
             "→ driver is high-Z on the bus.", size=SMALL)
        text(d, (12.0, y - 1.0), "D2 cathode → Q1 collector, anode → R8 / Data−.   "
             "Rbleed (Q2 collector → GND) added 2026-10-13, harmless, on the board.", size=SMALL)
        finish(d, "avclan_transceiver_tx")


def sheet_full():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=FONT, unit=2.4, lw=1.4, bgcolor="white")
        XM, XP = 4.6, 5.6            # vertical bus nets: Data- (left), Data+ (right)
        XMCU = 21.0                  # left edge of the RP2040-Zero box
        y_rx = 7.0
        y_tx = 3.0
        draw_rx(d, y_rx, xm=XM, xp=XP, xout=XMCU)
        yc2, yd2, yb1 = draw_tx(d, y_tx, xm=XM, xp=XP, xin=XMCU)

        # bus nets
        y_h_p, y_h_m = 4.6, 3.6      # H1 pin rows
        wire(d, (XP, y_rx - 0.62), (XP, yc2))          # Data+  RX tap .. TX tap
        wire(d, (XM, y_rx + 0.62), (XM, yd2))          # Data-  RX tap .. TX tap
        dot(d, (XP, y_h_p))
        dot(d, (XM, y_h_m))
        text(d, (XP + 0.15, y_rx - 1.6), "Data+", size=FONT, halign="left")
        text(d, (XM - 0.15, yd2 + 1.0), "Data−", size=FONT, halign="right")
        # H1
        hx0, hx1 = 1.2, 3.2
        box(d, hx0, 2.9, hx1, 5.3)
        text(d, ((hx0 + hx1) / 2, 5.65), "H1  (2-pin, no GND)", size=FONT)
        wire(d, (hx1, y_h_p), (XP, y_h_p))             # crosses Data- without connecting
        wire(d, (hx1, y_h_m), (XM, y_h_m))
        text(d, (hx1 - 0.15, y_h_p), "L  \"T\"", size=SMALL, halign="right")
        text(d, (hx1 - 0.15, y_h_m), "R", size=SMALL, halign="right")
        text(d, (hx1 + 0.2, y_h_p + 0.28), "Data+", size=SMALL - 1, halign="left", color="#444")
        text(d, (hx1 + 0.2, y_h_m - 0.28), "Data−", size=SMALL - 1, halign="left", color="#444")
        wire(d, (hx0 - 0.9, y_h_p), (hx0, y_h_p))
        wire(d, (hx0 - 0.9, y_h_m), (hx0, y_h_m))
        text(d, (hx0 - 1.0, y_h_p), "car WHITE", size=SMALL, halign="right")
        text(d, (hx0 - 1.0, y_h_m), "car BROWN", size=SMALL, halign="right")
        text(d, ((hx0 + hx1) / 2 - 0.6, 2.35), "left/right as on the board, H1 facing down;", size=SMALL - 1)
        text(d, ((hx0 + hx1) / 2 - 0.6, 1.9), "the old silk had Data± swapped", size=SMALL - 1)

        # RP2040-Zero
        bx0, bx1, by0, by1 = XMCU, XMCU + 4.0, yb1 - 1.0, y_rx + 2.0
        box(d, bx0, by0, bx1, by1)
        text(d, ((bx0 + bx1) / 2, by1 + 0.4), "U1  RP2040-Zero", size=FONT + 1)
        pins = [(y_rx, "GP0  AVC RX (PIO)"), (yb1, "GP1  AVC TX (PIO)")]
        for y, s in pins:
            dot(d, (bx0, y))
            text(d, (bx0 + 0.2, y), s, size=SMALL, halign="left")
        # power pins with their rail names
        for y, s, kind in [(3.0, "3V3", "sup"), (1.6, "5V", "sup"), (0.2, "GND", "gnd")]:
            wire(d, (bx0 - 1.2, y), (bx0, y))
            text(d, (bx0 + 0.2, y), s, size=SMALL, halign="left")
            if kind == "sup":
                text(d, (bx0 - 1.45, y), "3V3" if s == "3V3" else "+5 V", size=FONT, halign="right")
                dot(d, (bx0 - 1.2, y))
            else:
                gnd(d, (bx0 - 1.2, y))
        text(d, (bx0 + 0.2, 1.1), "(shared with LM339 / Q2)", halign="left", size=SMALL - 1, color="#444")

        # notes
        nx, ny = 0.6, yb1 - 2.4
        notes = [
            "NOTES",
            "• RX polarity: dominant (Data+ above Data−) → LM339 OUT HIGH → GP0 HIGH;  firmware setting  pol hi.",
            "• Rbias (220 kΩ, pin 3 → pin 6) sets IN− ≈ +105 mV above Data− in the car (+215 mV on the bench)"
            " → idle reads LOW.  No feedback resistor.",
            "• TX: GP1 HIGH = dominant (Q1 sinks Data−, Q2 sources Data+).  GP1 idles LOW = recessive, driver high-Z."
            "  Never idle GP1 high.",
            "• Car bus: common mode ≈ 2.6 V;  idle WHITE − BROWN ≈ +50 mV;  dominant: BROWN ≈ −0.5 V,"
            " WHITE ≈ +0.1 V vs idle (≈ 0.6 V diff).",
            f"• RX values measured on the board 2026-10-14.  TX values = {TX_SET}.",
            "• All grounds common (RP2040 GND, LM339 pin 12, Q1 emitter); 5 V = RP2040 5 V/USB, 3V3 = RP2040 3V3 out.",
        ]
        box(d, nx, ny - 0.55 * len(notes) - 0.2, 26.0, ny + 0.4)
        for i, s in enumerate(notes):
            text(d, (nx + 0.3, ny - 0.55 * i), s, size=SMALL + (1 if i == 0 else 0), halign="left")
        text(d, (13.3, y_rx + 5.4), "AVC-LAN (IEBus) transceiver for RP2040-Zero — as built", size=FONT + 3)
        finish(d, "avclan_transceiver_full")


if __name__ == "__main__":
    sheet_rx()
    sheet_tx()
    sheet_full()
    print("done")
