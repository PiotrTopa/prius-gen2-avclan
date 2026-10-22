# 1. Bus basics: framing, timing, ACK and electrical levels

AVC-LAN is Toyota's name for its audio/visual bus. On the wire it behaves like NEC's IEBus
(Inter Equipment Bus): a two-wire differential, half-duplex, multi-master bus. Each bit is coded
by the width of a dominant pulse. Everything in this chapter was measured on one 2004–2009
Prius (NHW20) with the factory navigation multi-display. A general logic analyser with a
comparator front end is enough to reproduce it. Appendix [A1](A1-transceiver-hardware.md)
describes the receiver and driver that were used.

Verification tags used in this file: **SCOPE** = measured with an oscilloscope or meter on the
car's bus; **DECODE** = follows from decoding many frames with zero parity errors; **TX** =
confirmed by transmitting frames that the car's units accepted (ACKed and acted on);
**IEBus** = matches NEC's published IEBus behaviour, but not checked separately on this car.

## 1.1 Electrical layer

| Property | Value on this car | How verified, date |
|---|---|---|
| Wires | twisted pair, **Data+** and **Data−**; no ground in the pair, so the receiver must share chassis ground with the car | SCOPE, 2026-10-07/14. A tap with a floating ground decoded 0 frames |
| Wire colours at the tap used | **white = Data+**, **brown = Data−** (other harness points may use other colours) | SCOPE, 2026-10-14 |
| Common mode | ≈ 2.6 V (white ≈ 2.75 V, brown ≈ 2.45 V mean with traffic) | SCOPE, 2026-10-14 |
| Idle (recessive) differential | Data+ − Data− ≈ +50…+100 mV (white slightly above brown) | SCOPE, 2026-10-14 |
| Dominant | Data− falls by ≈ 0.5 V and Data+ rises by ≈ 0.1 V, so the differential is ≈ 0.6 V with **Data+ above Data−** | SCOPE, 2026-10-14 |
| Dominant sense | dominant = Data+ pulled above Data−; recessive = both released to the common mode | SCOPE + TX |
| Bus asleep (car off) | a powered receiver reads the unpowered pair as permanently "dominant", or stuck. That is not traffic: wait for ACC/READY | SCOPE, 2026-10-07/08/12 |

> **Receiver threshold.** The idle differential is only tens of millivolts, so a comparator with
> zero threshold rests wherever its offset puts it. In practice it often reads "dominant" at idle.
> The receiver needs a deliberate bias of about 100–150 mV towards recessive. See
> [A1](A1-transceiver-hardware.md).

## 1.2 Bit coding

Every bit begins with a dominant pulse inside a fixed slot. The pulse width carries the value.

| Symbol | Dominant width | Recessive gap after it | Slot | Verified |
|---|---|---|---|---|
| Start bit | ≈ 166–172 µs | ≈ 19–30 µs | — | SCOPE + DECODE, 2026-10-07 |
| Logic **1** | ≈ 20 µs | ≈ 19 µs | ≈ 39 µs | SCOPE + DECODE |
| Logic **0** | ≈ 32–34 µs | ≈ 7 µs | ≈ 39 µs | SCOPE + DECODE |

- Raw pulse captures of the car's own frames (2026-10-07 and 2026-10-12) cluster tightly at
  20 / 32–34 / 170 µs dominant, with gaps of 19 / 7 µs (18 / 6 µs after our receiver, which
  adds ≈ 1 µs of delay). Decoding used these thresholds: dominant < 6 µs = glitch (ignored),
  < 26 µs = 1, < 100 µs = 0, < 400 µs = start, longer = bus stuck.
- A frame lasts about `166 + 19 + nbits × 39` µs. A unicast frame with 6 data bytes has
  1 + 13 + 14 + 6 + 10 + 6×10 = 104 bits, which is ≈ 4.2 ms.
- The bit period (≈ 39 µs) fits the faster of the two communication modes of NEC's µPD72042
  IEBus controller (nominally ≈ 17 kbit/s of effective throughput). That is our interpretation.
  We did not check it against the controller inside the car's units.

## 1.3 Frame layout

Bits go out MSB first. Every field except the broadcast bit carries an **even parity bit P**:
P is the XOR of the field's bits. Every field after the master address also carries an
**acknowledge slot A**.

```
start | B | master address (12) P | slave address (12) P A | control (4) P A |
      length (8) P A | data[0] (8) P A | data[1] (8) P A | ... | data[len-1] (8) P A
```

| Field | Meaning on this car | Verified |
|---|---|---|
| B (broadcast bit) | **0 = broadcast**, 1 = unicast. The "broadcast" addresses 1FF and FFF always came with B = 0 | DECODE, 142 777 frames 2026-10-07…19 |
| Master address | 12-bit physical address of the sender. No ACK slot | DECODE + TX |
| Slave address | 12-bit physical address of the receiver, or 1FF / FFF for broadcasts | DECODE + TX |
| Control | always **0xF** on this car. In IEBus this code means "write data" | DECODE: 142 776 of 142 777 frames were 0xF; the remaining one was a bit error. Meaning per IEBus |
| Length | number of data bytes. The longest seen here is 14. NEC's controller allows up to 32 | DECODE |
| Data | Toyota's message layer, see below | DECODE + TX |

### Toyota message layer inside the data bytes

| Kind | Data bytes | Example |
|---|---|---|
| Unicast | `00 <from-logical> <to-logical> <opcode> args…` | `110→178 00 25 58 84 01 00` (MENU button pressed) |
| Broadcast | `<from-logical> <to-logical> <opcode> args…` (no leading 00) | `110→FFF 12 01 60 5F 05 00 05` (active screen) |

Logical device IDs (`58` = navigation, `5D` = climate drawing, `E0` = climate control, …) are
listed in [02-devices.md](02-devices.md). The broadcast `to-logical` is usually `01`
(communication control) or `31` (status listeners). The one exception: the display's broadcast
`110→FFF 00 01 07` does carry a leading `00` (seen in every capture that contains it).

A common pattern is that a reply uses **the request opcode + 0x10**: `8F→9F`, `8E→9E`,
`42→52`, `43→53`, `20→30`, `00→10`, `07→17`, `E0→F0`, `E4→F4`, `E6→F6`, `E8→F8`. The device
table request `01` is answered with `12`. This pattern was observed, not documented anywhere.
It helps when you meet a new opcode.

## 1.4 Acknowledge (ACK) behaviour

| Rule | Verified |
|---|---|
| In every ACK slot the **master sends a "1"** (a ≈ 20 µs pulse). The **addressed slave acknowledges by stretching that pulse to the length of a "0"** (≈ 32 µs). Reading the slot as 0 means ACK, reading it as 1 means NAK | TX, 2026-10-14: our receiver stretched the slot to 30 µs from 6 µs into it, and the display accepted the frames |
| Broadcast frames are not acknowledged (slots stay "1") | DECODE |
| If a unicast is not ACKed at the **slave-address** slot, the master aborts after 28 bits (start + B + 13 + 14) and **retries every ≈ 25 ms**. The display sent 464 such header-only attempts in 40 s to a nav emulator that did not ACK, and never progressed | TX/DECODE, 2026-10-14 |
| A unit that wants to talk to the display must ACK **every** frame addressed to it, in real time (inside the bit slot). A host that answers over USB is too slow for this; it has to be done in the receiver's interrupt or in hardware | TX, 2026-10-14 |
| An isolated NAK on a reply is usually harmless. Seen without effect: our `00 01 12 30 XX FF` ping replies, our `00 58 34 E0` setup message, one ident reply `9F…` (the display polls it again 30 s later), and one `1C6→110 00 E5 5F B7…` | DECODE, 2026-10-14 and 2026-10-19 |

## 1.5 Arbitration and reply timing

| Observation | Value | Verified |
|---|---|---|
| Two units answering the same broadcast | the climate/trip gateway (1C6) starts its roll-call reply ≈ 2.5 ms after the roll call ends. The genuine nav starts within ≈ 0.5 ms. A third party answering at ≈ 8 ms collided and was NAKed | DECODE + TX, 2026-10-14 |
| Genuine nav reply latency to a display request | 4–8 ms (frame end to frame end) | DECODE, 2026-10-07 |
| Minimum bus idle before our transmitter started a frame | 250 µs worked reliably | TX |
| Bus load (whole bus, car READY) | ≈ 14–16 frames/s on average (35 227 frames in a 42-minute drive) | DECODE, 2026-10-14 |

## 1.6 Physical addresses vs logical IDs

A **physical address** (12 bits: `110`, `178`, `1C6`, …) identifies a box on the bus. A box
hosts one or more **logical devices** (8 bits: `58`, `E0`, `5D`, …), which are the functions
named inside the data bytes. A box announces its logical devices in the startup roll call
([02-devices.md](02-devices.md)).

## 1.7 Timing as measured with the RP2040 transceiver firmware

These are the parameters of the transceiver firmware in `firmware/` (see the README). Every
capture and emulation run in this repository used them, and they are the ones that work
against the car.

| Item | Value |
|---|---|
| TX start bit | 166 µs dominant + 19 µs recessive |
| TX "1" | 20 µs dominant + 19 µs recessive (39 µs period) |
| TX "0" | 32 µs dominant + 7 µs recessive (39 µs period) |
| TX frame duration | `166 + 19 + 39 × nbits` µs, with `nbits = 44 + 10 × (number of data bytes)` (1 broadcast + 13 master + 14 slave + 6 control + 10 length, then 10 per byte) |
| RX sampling | 4 MHz (0.5 µs resolution), ≈ 1 µs debounce |
| RX classification by dominant width | < 6 µs glitch (ignored), < 26 µs "1", < 100 µs "0", < 400 µs start, else bus stuck |
| RX resynchronisation | a start bit always restarts decoding, even mid-frame. A frame is abandoned after 600 µs with no dominant pulse. A parity error drops the frame |
| Data length | 0–32 bytes |
| ACK slot | starts 39 µs after the start of the parity bit. The firmware, acting as slave, drives dominant from 6 µs to 30 µs into the slot, so the master sees a ≈ 32 µs "0" (ACK). Without it the master aborts at the address field: the display's unicasts to 178 die unless some device ACKs them |
| TX bus access | waits for 250 µs of bus silence. The transceiver hears its own frame (echo). NAK = the addressed slave did not ACK |
| Auto-reply latency | a reply stored in the firmware (e.g. to the roll call) starts ≈ 0.3 ms after the triggering frame ends. The climate/trip gateway answers the roll call at ≈ 2.5 ms, so an emulated nav replying from firmware wins, as the genuine nav does |
| RX polarity auto-detection | 3000 samples, 20 µs apart; the majority level is taken as idle (the bus is idle far more often than active) |
