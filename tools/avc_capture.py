#!/usr/bin/env python3
"""
avc_capture — log everything the transceiver says, losslessly, for later analysis.

  avc_capture.py OUT.ndjson [--port P] [--seconds N] [--pol auto|hi|lo] [--raw] [--errors]

One JSON object per line, appended to OUT:
  {"ht": <unix time>, "start": <port>, ...}        first line of a session
  {"ht": .., "hm": <host monotonic s>, "raw": "<line as received>", "obj": {..}}
                                                   one per firmware line ("obj" only if it parsed)
  {"ht": .., "mark": n}                            SIGUSR1 marker (e.g. "ignition on")
  {"ht": .., "stop": <lines logged>}               last line of a session

Stops on Ctrl-C / SIGTERM / --seconds. `kill -USR1 <pid>` writes a marker line.
--pol forces the RX polarity before logging; --raw also logs raw pulse widths
(avc_raw on), --errors also logs decode errors (avc_err on); both are switched
off again on exit.
"""
import argparse
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from avcctl import find_port, open_port, send  # noqa: E402

stop = False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", help="output .ndjson file (appended)")
    ap.add_argument("--port")
    ap.add_argument("--seconds", type=float, help="stop after this many seconds")
    ap.add_argument("--pol", choices=["auto", "hi", "lo"], help="force RX polarity first (avc_cfg pol)")
    ap.add_argument("--raw", action="store_true", help="also log raw pulse widths (avc_raw)")
    ap.add_argument("--errors", action="store_true", help="also log decode errors (avc_err)")
    args = ap.parse_args()

    def on_term(*_):
        global stop
        stop = True

    pending = []

    def on_mark(*_):
        pending.append(time.time())

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, on_mark)

    port = find_port(args.port)
    t_end = None if args.seconds is None else time.monotonic() + args.seconds
    n = marks = 0
    with open_port(port) as ser, open(args.out, "a", buffering=1) as f:
        f.write(json.dumps({"ht": time.time(), "start": port, "pol": args.pol,
                            "raw": args.raw, "errors": args.errors}) + "\n")
        if args.pol:
            send(ser, {"id": 0, "d": {"a": "avc_cfg", "pol": args.pol}})
        if args.raw:
            send(ser, {"id": 0, "d": {"a": "avc_raw", "on": True}})
        if args.errors:
            send(ser, {"id": 0, "d": {"a": "avc_err", "on": True}})
        while not stop and (t_end is None or time.monotonic() < t_end):
            while pending:
                marks += 1
                f.write(json.dumps({"ht": pending.pop(0), "mark": marks}) + "\n")
            raw = ser.readline()
            if not raw:
                continue
            rec = {"ht": time.time(), "hm": time.monotonic(),
                   "raw": raw.decode(errors="replace").rstrip()}
            try:
                rec["obj"] = json.loads(raw)
            except ValueError:
                pass
            f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            n += 1
        if args.raw:
            send(ser, {"id": 0, "d": {"a": "avc_raw", "on": False}})
        if args.errors:
            send(ser, {"id": 0, "d": {"a": "avc_err", "on": False}})
        f.write(json.dumps({"ht": time.time(), "stop": n}) + "\n")
    print(f"# {n} lines -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
