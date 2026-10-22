# Host tools

Python 3.8+ and [pyserial](https://pypi.org/project/pyserial/) (`pip install pyserial`).
All tools talk to the [firmware](../firmware/README.md) over its USB serial port.
The port is found automatically (`--port`, else `$AVC_PORT`, else the first
`/dev/serial/by-id/*AVC-LAN_Transceiver*`, else the first `/dev/ttyACM*` /
`/dev/cu.usbmodem*`). Only one program can hold the port at a time.

| Tool | Purpose |
|---|---|
| `avcctl.py` | small CLI + the serial helpers the other tools import: monitor, whoami, stats, cfg, raw pulses, send a frame, list auto-reply slots, bootsel/reset |
| `avc_capture.py` | lossless logger: every line the firmware sends, with host timestamps |
| `nav_emu.py` | emulates the Prius (gen 2) navigation ECU (AVC-LAN `178`) towards the display |
| `touch_console.py` | browser view of touch coordinates / hardware buttons, fed by a running log |

## Quick checks

```bash
./avcctl.py whoami                      # {"msg":"IDENT","role":"avclan","ver":"3.2.0"}  rtt=…
./avcctl.py monitor --hb                # decoded frames + heartbeats, human-readable
./avcctl.py cfg --pol hi                # force RX polarity (see the firmware README)
./avcctl.py raw --seconds 5 --csv p.csv # raw dominant/gap widths: expect clusters at ≈20, ≈32, ≈166 µs
./avcctl.py avc 178 110 15 00 58 12 52 02 01   # transmit; prints the echo (watch for "nak":1)
./avcctl.py stats
```

## Capturing traffic

```bash
./avc_capture.py drive1.ndjson --pol hi            # until Ctrl-C
./avc_capture.py idle.ndjson --seconds 60 --errors # also log decode errors
kill -USR1 <pid>                                   # drop a numbered marker into the log
```

Open the port **before** the car wakes the bus: the firmware drops lines while no
host has the port open. The file is appended to, one JSON object per line.

## Running the navigation ECU emulator

With the real navigation ECU disconnected and the transceiver on the AVC-LAN pair:

```bash
./nav_emu.py nav.ndjson --pol hi --fw-auto --fw-ack
```

Start it before the car is switched on: the display (`110`) only talks to a nav that
answers its startup roll call (`110 → FFF  12 01 00`).

* `--fw-ack` sets `avc_cfg ack 178`: the firmware acknowledges, in real time, every
  frame addressed to `178`. Without it the display's requests die unacknowledged at
  the address field and never reach the host.
* `--fw-auto` loads auto-reply slots 0 and 1 so the firmware itself answers the roll
  call `12 01 00` / `12 01 01` about 0.3 ms after it ends — a reply from the host
  arrives too late (~2.5 ms) and collides with another ECU's answer.
* `--pol auto|hi|lo` RX polarity for your PHY (default `auto`).

Other options: `--lang 02|06` (UI language byte, English/Dutch), `--ident …`,
`--time-fmt old|new`, `--no-burst`, `--no-btn-ack`, `--no-release-ack`,
`--announce` (bus already awake: send the roll-call answers unsolicited),
`--rc-delay MS` / `--rc-retries N` (host-side roll-call answer when not using
`--fw-auto`), `--raw` (also log raw pulses), `--blind` (transmit on timers without
RX). On exit (Ctrl-C) the ACK address and auto-reply slots are cleared again.
The reply tables in `nav_emu.py` are what a real nav ECU sends; see the comments
there for each request/answer pair.

The emulator prints notes such as `display screen -> 58`, `TOUCH 7A 40 7A 40`,
`BUTTON 01`, and on exit a summary `tx=…, echoes=…, display->178 NAKed=…`.

### Touch console

```bash
./touch_console.py nav.ndjson           # then open http://localhost:8766
./touch_console.py nav.ndjson --replay  # load the whole file first
```

It tails the log, so it runs next to the emulator (or `avc_capture.py`) that owns the
serial port. It shows `110 → 178  00 21 24 78 X Y X Y` touch frames (one byte per axis,
`00 00 00 00` = release) on a canvas with adjustable calibration, and the hardware
buttons `00 25 58 84 KK 00` (`01` menu, `04` dest, `02` map, `00` release).

## Log line format

`avc_capture.py` and `nav_emu.py` write JSON lines (NDJSON):

| Line | Written by | Fields |
|---|---|---|
| received line | both | `hm` host monotonic clock (s), `raw` the line exactly as received, `obj` the parsed object (absent if it did not parse), `ht` host Unix time (s) |
| session start / stop | `avc_capture.py` | `{"ht":…,"start":"<port>","pol":…,"raw":…,"errors":…}`, `{"ht":…,"stop":<lines>}` |
| marker | `avc_capture.py` | `{"ht":…,"mark":n}` (SIGUSR1) |
| transmitted frame | `nav_emu.py` | `{"tx":{"m":"178","s":"110","c":15,"d":[…],"b":true?},"ht":…}` — as sent to the firmware; the bus echo follows as a received line with `"echo":1` |
| note | `nav_emu.py` | `{"note":"<text>","ht":…}` — what the emulator printed |

Example:

```json
{"ht":1792671841.18,"hm":5123.402,"raw":"{\"id\":2,\"ts\":81234,\"seq\":17,\"d\":{\"m\":\"110\",\"s\":\"178\",\"c\":15,\"d\":[\"00\",\"12\",\"58\",\"8F\"]}}","obj":{"id":2,"ts":81234,"seq":17,"d":{"m":"110","s":"178","c":15,"d":["00","12","58","8F"]}}}
{"tx":{"m":"178","s":"110","c":15,"d":["00","58","12","9F","02","F9","D1","13","0A","58","A6","9A","80","80"]},"ht":1792671841.18}
```

`obj.ts` is the firmware's clock (ms since boot, when the frame ended) and is the
right one for inter-frame timing; `hm`/`ht` include USB and host scheduling jitter.
