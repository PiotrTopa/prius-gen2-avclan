# Prius Gen 2 (NHW20) AVC-LAN protocol notes

Reverse-engineered documentation of the AVC-LAN bus in a **Toyota Prius second generation
(NHW20, model years 2004–2009)**. The car has the factory **navigation multi-display** (the
touch screen, here called "the display") and the **JBL** audio package. The notes cover:

- the bus itself: framing, bit timing, acknowledge behaviour, electrical levels;
- the units on the bus and their startup roll call;
- everything the display sends and receives: active screen, touch coordinates, keys, screen
  ownership;
- the gateway's climate, outside-temperature, energy-monitor and battery frames, with
  verified bit maps;
- the **complete dialogue needed to replace the factory navigation ECU**: with it the display
  accepts a third-party "nav" and switches to its video input;
- what is *not* on the bus in this car;
- a hardware appendix for a simple comparator-based transceiver.

It is written for an engineer who wants to build their own nav emulator, read the car's climate
and energy data, or control the climate system from another device.

## How this was obtained

The bus of the author's own car was observed with a self-built receiver (Appendix A1) between
2026-10-07 and 2026-10-19:

- **Passive captures** with an operator noting each action ("pressed fan 5 now"), so frames
  could be matched to events.
- **Correlation with CAN/OBD data** recorded at the same time, for the energy-monitor bits.
- **Unplug tests**: the factory nav removed and the traffic compared.
- **Active tests**: frames transmitted onto the bus and the car's reaction observed, including
  a full emulation of the navigation ECU.

All captures were taken by the author, on the author's car, for interoperability. No Toyota
software, firmware, service documentation or other copyrighted material was used or is
reproduced here.

## Legal note

- This repository is published for **research, education and interoperability**. It is
  provided "as is" under the MIT licence, without warranty. Transmitting on a vehicle bus can
  disturb the car's displays and controls. You do so at your own risk. Never test while driving.
- **AVC-LAN** is Toyota's name for its audio/visual bus. The physical and data-link layers
  follow **IEBus**, a bus standard of NEC (now Renesas). Toyota, Prius, JBL, Denso, AVC-LAN
  and IEBus are trademarks of their respective owners. They are used here only to identify
  the products concerned. This project is not affiliated with or endorsed by any of them.
- The captures contain only bus traffic of the car's own units: no vehicle identification,
  location or personal data.

## How to read the docs

Start with 01 and 02, then jump to what you need.

| File | Content |
|---|---|
| [docs/01-bus-basics.md](docs/01-bus-basics.md) | electrical levels, bit timing, frame layout, ACK, reply timing |
| [docs/02-devices.md](docs/02-devices.md) | physical addresses `110`/`178`/`1C6`, logical IDs, roll call, re-registration |
| [docs/03-display-messages.md](docs/03-display-messages.md) | active screen, periodic broadcasts, lights, touch, keys, screen request/grant/release |
| [docs/04-climate-and-vehicle.md](docs/04-climate-and-vehicle.md) | outside temperature, climate status/set temperature/keys, energy monitor arrows, battery bars, EV mode |
| [docs/05-nav-emulation.md](docs/05-nav-emulation.md) | the full navigation-ECU emulation dialogue and its hard requirements |
| [docs/06-touch-calibration.md](docs/06-touch-calibration.md) | raw touch ranges and the mapping to the 480 × 240 picture; key codes |
| [docs/07-what-is-not-on-the-bus.md](docs/07-what-is-not-on-the-bus.md) | amplifier roll-call test, aftermarket radio, things that stay local |
| [docs/08-open-questions.md](docs/08-open-questions.md) | unknown bytes, **clearly labelled guesses**, differences from other Toyota models |
| [docs/A1-transceiver-hardware.md](docs/A1-transceiver-hardware.md) | the receiver/driver used, as built and measured, with lessons learned |
| [examples/](examples/) | short capture excerpts in CSV, with the format described |

**Notation.** `110→178 00 25 58 84 01 00` means master (sender) `110`, slave (receiver)
`178`, data bytes `00 25 58 84 01 00`, all hex. The control field (always `F`) and the length
are left out. `(B)` marks a broadcast. For unicasts the data bytes are
`00 <from-logical> <to-logical> <opcode> args…` ([01 §1.3](docs/01-bus-basics.md#13-frame-layout)).

**Verification tags.** Every table row says how it was verified and on which capture date.
The tags are: confirmed by the operator on the car's display (USER), correlated with CAN data
(CAN), transmitted by us with the car reacting as described (TX/REQ), observed from the
genuine unit (REAL), structure only (DECODE), or inferred (INF). Guesses appear only as INF and
in [08-open-questions.md](docs/08-open-questions.md).

## Status and limitations

- **One car.** A European-market NHW20 with the factory navigation display and JBL audio. The
  factory head unit had been replaced by an aftermarket radio before the captures. Other
  markets, trims or a stock head unit may add units (`190`, `440`, …) and messages.
- **About 143 000 decoded frames** from 2026-10-07 to 2026-10-19, including a 42-minute drive.
- Verified and used in practice: the outside temperature, the climate status, set temperature
  and keys (including remote control), the energy-monitor arrows, the battery bars, EV mode,
  touch and keys, and the complete nav emulation including the language selection.
- Open: several 1C6 fields (engine/power-like values, distance, shift) and the meaning of the
  nav's identification and device-table bytes. See [08](docs/08-open-questions.md).

## Firmware and tools

A standalone RP2040 transceiver firmware and host tools live in [`firmware/`](firmware/) and
[`tools/`](tools/): a capture logger (`avc_capture.py`), a command-line client (`avcctl.py`),
the navigation emulator (`nav_emu.py`) and a touch viewer (`touch_console.py`). Their own
README files document their usage.

## References (prior art)

- softservice.com.pl, *Toyota Corolla AVC-LAN* page:
  <http://www.softservice.com.pl/corolla/avc/avclan.php>. This is the source of the physical
  address list (`110` EMV, `178` NAVI, `1C6` G/W, `190`/`160` head unit, `440` DSP-AMP, …) and
  the logical device names. What agrees and what differs is listed in
  [08 §8.3](docs/08-open-questions.md#83-differences-from-published-prior-art-other-toyota-models).
  In short: bit timing, frame layout, the touch frame and the addresses agree. The roll-call
  interpretation, logical `85`, and the absence of audio units differ.
- sigmaobjects.com, *Toyota* AVC-LAN pages (<http://www.sigmaobjects.com/toyota/>). Often
  cited in earlier AVC-LAN projects. The site could not be reached when this was written
  (2026-10-22), so nothing here is checked against it.
- NEC (Renesas), *µPD72042 IEBus controller* data sheet: the IEBus physical/data-link layer
  (broadcast bit, 12-bit addresses, control field, parity and acknowledge bits; communication
  modes of ≈ 3.9 and ≈ 17 kbit/s).

## Contributing

Corrections, confirmations of the guesses in [08](docs/08-open-questions.md), and captures from
other NHW20 variants are welcome as issues or pull requests. Please:

- state the car (market, year, equipment) and the capture date;
- say how each claim was verified (on-screen confirmation, CAN correlation, replay), and keep
  guesses labelled as guesses;
- strip anything personal from captures (VIN, locations, phone names) before sharing;
- use the CSV format of [examples/](examples/README.md) for excerpts.

## Licence

MIT. See [LICENSE](LICENSE).
