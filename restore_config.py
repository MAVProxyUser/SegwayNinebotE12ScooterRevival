#!/usr/bin/env python3
"""Restore motor + app config from backups/, one write at a time with settling.

Deliberately slow: VESC commits config to flash with interrupts disabled, and
stacking writes too quickly is what hung the ESC on 2026-10-17.
"""
import glob, pathlib, sys, time, serial
from vesc_read import frame, read_packet, find_port

SET_MC, SET_APP, GET_MC, GET_APP = 13, 16, 14, 17


def xfer(payload, want, settle=3.0, t=4.0):
    with serial.Serial(find_port(), 115200, timeout=0.3) as ser:
        time.sleep(0.3); ser.reset_input_buffer()
        ser.write(frame(payload))
        end = time.time() + t
        got = None
        while time.time() < end:
            p = read_packet(ser, timeout=max(0.1, end - time.time()))
            if p and (want is None or p[0] == want):
                got = p; break
    time.sleep(settle)
    return got


def newest(pat):
    hits = sorted(glob.glob(f"backups/{pat}"))
    if not hits: sys.exit(f"no backups/{pat}")
    return pathlib.Path(hits[-1]).read_bytes()


for label, blob, setid, getid in [
    ("motor", newest("motor-*.bin"), SET_MC,  GET_MC),
    ("app",   newest("app-*.bin"),   SET_APP, GET_APP),
]:
    print(f"writing {label} config ({len(blob)} B) ...", flush=True)
    xfer(bytes([setid]) + blob, None, settle=4.0)
    chk = xfer(bytes([getid]), getid, settle=1.0)
    ok = chk and bytes(chk[1:]) == blob
    print(f"  {label}: {'OK' if ok else '*** MISMATCH — retry after a power cycle ***'}")
