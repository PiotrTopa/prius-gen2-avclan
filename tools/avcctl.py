#!/usr/bin/env python3
"""
avcctl — talk to the AVC-LAN transceiver firmware over USB-CDC (NDJSON lines).

  avcctl.py monitor [--hb] [--latency]        stream everything the firmware says
  avcctl.py whoami                            IDENT round trip (also measures RTT)
  avcctl.py stats                             counters snapshot
  avcctl.py cfg [--pol auto|hi|lo] [--ack 178|000] [--t1 US] [--t0 US] [--tstart US] [--glitch US]
  avcctl.py raw [--seconds N] [--csv FILE]    raw dominant/gap widths (PHY bring-up)
  avcctl.py avc M S C [D ...] [--broadcast]   transmit a frame (M, S, D hex; C decimal 0..15)
  avcctl.py auto                              list the auto-reply slots and their hit counts
  avcctl.py send '<json line>' [--wait S]     send a raw command line, print the replies
  avcctl.py bootsel                           reboot into the UF2 bootloader
  avcctl.py reset                             watchdog reboot

Port: --port, else $AVC_PORT, else the first /dev/serial/by-id/*AVC-LAN_Transceiver*,
else the first /dev/ttyACM* (Linux) / /dev/cu.usbmodem* (macOS).

Also importable: find_port(), open_port(), send(), lines() are what avc_capture.py
and nav_emu.py use.
"""
import argparse
import glob
import json
import os
import sys
import time


def find_port(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("AVC_PORT"):
        return os.environ["AVC_PORT"]
    for pattern in ("/dev/serial/by-id/*AVC-LAN_Transceiver*", "/dev/ttyACM*", "/dev/cu.usbmodem*"):
        cands = sorted(glob.glob(pattern))
        if cands:
            return cands[0]
    sys.exit("no transceiver port found; use --port or $AVC_PORT")


def open_port(path):
    try:
        import serial
    except ImportError:
        sys.exit("pyserial missing: pip install pyserial")
    # USB CDC ignores the baud rate; any value works.
    return serial.Serial(path, 1_000_000, timeout=0.05)


def send(ser, obj):
    """Write one command object as a compact JSON line; returns the line."""
    line = json.dumps(obj, separators=(",", ":")) + "\n"
    ser.write(line.encode())
    return line


def lines(ser, seconds=None):
    """Yield (host_monotonic, parsed_or_None, raw_text) until `seconds` elapse."""
    t_end = None if seconds is None else time.monotonic() + seconds
    while t_end is None or time.monotonic() < t_end:
        raw = ser.readline()
        if not raw:
            continue
        now = time.monotonic()
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        yield now, obj, raw.decode(errors="replace").rstrip()


def fmt_avc(d):
    data = " ".join(d.get("d", []))
    flags = ",".join(k for k in ("b", "nak", "echo") if d.get(k))
    return f"{d.get('m')}->{d.get('s')} c={d.get('c'):X} [{data}]" + (f" {{{flags}}}" if flags else "")


def cmd_monitor(args, ser):
    print(f"# monitoring {ser.port} (Ctrl-C to stop)")
    prev = None
    for host_t, obj, raw in lines(ser):
        if obj is None:
            print("?", raw)
            continue
        dev = obj.get("id")
        stamp = time.strftime("%H:%M:%S") + f".{int((host_t % 1) * 1000):03d}"
        if dev == 2 and "m" in obj.get("d", {}):
            extra = ""
            if args.latency and prev is not None and obj.get("ts") is not None:
                d_host = (host_t - prev[0]) * 1000.0
                d_fw = obj["ts"] - prev[1]
                extra = f"  dt_host={d_host:7.1f}ms dt_fw={d_fw:5d}ms skew={d_host - d_fw:+6.1f}ms"
            if obj.get("ts") is not None:
                prev = (host_t, obj["ts"])
            print(f"{stamp} AVC  {fmt_avc(obj['d'])}{extra}")
        else:
            d = obj.get("d", {})
            if d.get("msg") == "GW_HB" and not args.hb:
                continue
            print(f"{stamp} {'SYS' if dev == 0 else 'AVC'}  {json.dumps(d)}")


def wait_for(ser, pred, seconds=2.0):
    for host_t, obj, raw in lines(ser, seconds):
        if obj and pred(obj):
            return host_t, obj, raw
    return None


def cmd_whoami(args, ser):
    ser.reset_input_buffer()
    t0 = time.monotonic()
    send(ser, {"id": 0, "d": {"a": "whoami"}})
    r = wait_for(ser, lambda o: o.get("id") == 0 and o["d"].get("msg") == "IDENT")
    if not r:
        sys.exit("no IDENT reply")
    print(json.dumps(r[1]["d"]), f"  rtt={1000 * (r[0] - t0):.1f} ms")


def cmd_stats(args, ser):
    ser.reset_input_buffer()
    send(ser, {"id": 0, "d": {"a": "stats"}})
    r = wait_for(ser, lambda o: o.get("id") == 0 and "stats" in o["d"])
    if not r:
        sys.exit("no stats reply")
    print(json.dumps(r[1]["d"]["stats"], indent=2))


def cmd_cfg(args, ser):
    d = {"a": "avc_cfg"}
    for k in ("pol", "ack", "t1", "t0", "tstart", "glitch"):
        v = getattr(args, k)
        if v is not None:
            d[k] = v
    ser.reset_input_buffer()
    print(send(ser, {"id": 0, "d": d}).strip())
    r = wait_for(ser, lambda o: o.get("id") == 0 and "avc_cfg" in o["d"])
    print(r[2] if r else "no reply")


def cmd_raw(args, ser):
    send(ser, {"id": 0, "d": {"a": "avc_raw", "on": True}})
    out = open(args.csv, "w") if args.csv else None
    if out:
        out.write("kind,us\n")
    n = 0
    try:
        for _, obj, raw in lines(ser, args.seconds):
            if not obj or obj.get("id") != 0 or "avc_raw" not in obj["d"]:
                continue
            vals = obj["d"]["avc_raw"]
            if not isinstance(vals, list):
                continue
            n += len(vals)
            if out:
                for v in vals:
                    out.write(("gap,%d\n" % -v) if v < 0 else ("dom,%d\n" % v))
            else:
                print(" ".join(f"{v:+d}" for v in vals))
    finally:
        send(ser, {"id": 0, "d": {"a": "avc_raw", "on": False}})
        if out:
            out.close()
    print(f"# {n} pulses captured", file=sys.stderr)


def cmd_avc(args, ser):
    d = {"m": args.master, "s": args.slave, "c": int(args.control), "d": [x.upper() for x in args.data]}
    if args.broadcast:
        d["b"] = True
    print(send(ser, {"id": 2, "d": d}).strip())
    r = wait_for(ser, lambda o: (o.get("id") == 2 and o["d"].get("echo")) or
                 (o.get("id") == 0 and "err" in o["d"]), 1.0)
    print(r[2] if r else "no echo (is the RX side wired? the frame comes back tagged \"echo\":1)")


def cmd_auto(args, ser):
    ser.reset_input_buffer()
    send(ser, {"id": 2, "d": {"a": "auto"}})
    r = wait_for(ser, lambda o: o.get("id") == 2 and isinstance(o["d"].get("auto"), list))
    print(json.dumps(r[1]["d"]["auto"]) if r else "no reply")


def cmd_send(args, ser):
    ser.write((args.line.strip() + "\n").encode())
    for _, obj, raw in lines(ser, args.wait):
        print(raw)


def cmd_simple(action):
    def run(args, ser):
        print(send(ser, {"id": 0, "d": {"a": action}}).strip())
        for _, obj, raw in lines(ser, 0.5):
            print(raw)
    return run


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("monitor", help="stream everything")
    p.add_argument("--latency", action="store_true", help="show firmware-vs-host inter-frame timing skew")
    p.add_argument("--hb", action="store_true", help="also show heartbeats")
    p.set_defaults(fn=cmd_monitor)
    sp.add_parser("whoami", help="IDENT round trip").set_defaults(fn=cmd_whoami)
    sp.add_parser("stats", help="counters snapshot").set_defaults(fn=cmd_stats)
    p = sp.add_parser("cfg", help="avc_cfg: polarity, ACK address, thresholds")
    p.add_argument("--pol", choices=["auto", "hi", "lo"])
    p.add_argument("--ack", help="slave address whose ACK slots the firmware stretches (000 = off)")
    for k in ("t1", "t0", "tstart", "glitch"):
        p.add_argument(f"--{k}", type=int, help="threshold in us")
    p.set_defaults(fn=cmd_cfg)
    p = sp.add_parser("raw", help="raw pulse widths")
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--csv")
    p.set_defaults(fn=cmd_raw)
    p = sp.add_parser("avc", help="transmit a frame")
    p.add_argument("master", help="12-bit hex, e.g. 178")
    p.add_argument("slave", help="12-bit hex, e.g. 110 (FFF = broadcast)")
    p.add_argument("control", help="decimal 0..15 (15 = normal)")
    p.add_argument("data", nargs="*", help="hex bytes")
    p.add_argument("--broadcast", action="store_true", help="force the broadcast bit (default: only for FFF)")
    p.set_defaults(fn=cmd_avc)
    sp.add_parser("auto", help="list auto-reply slots").set_defaults(fn=cmd_auto)
    p = sp.add_parser("send", help="send a raw JSON line")
    p.add_argument("line")
    p.add_argument("--wait", type=float, default=1.0)
    p.set_defaults(fn=cmd_send)
    sp.add_parser("bootsel", help="reboot into the UF2 bootloader").set_defaults(fn=cmd_simple("bootsel"))
    sp.add_parser("reset", help="watchdog reboot").set_defaults(fn=cmd_simple("reset"))

    args = ap.parse_args()
    with open_port(find_port(args.port)) as ser:
        try:
            args.fn(args, ser)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
