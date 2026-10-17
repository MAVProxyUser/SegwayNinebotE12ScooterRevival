#!/usr/bin/env python3
"""
vesc_spin.py -- minimal "will the motor turn at all?" test over USB.

Uses the firmware's own `foc_openloop <current> <erpm>` terminal command, which
rotates a current vector in open loop. It needs NO motor detection, NO motor
configuration and NO sensors -- the ESC just drags the rotor around. The current
is given explicitly, so the VESC's (large, default) current limits don't apply.

    python3 vesc_spin.py --yes                        # 2 A, ramp to 500 erpm, 4 s
    python3 vesc_spin.py --yes -c 3 -e 1000 -s 5
    python3 vesc_spin.py --yes --reverse

THE MOTOR WILL TURN. Wheel clamped, off the ground, nothing near the tire.
Refuses to run without --yes.
"""

import argparse
import sys
import time

import serial

from vesc_read import (COMM_ALIVE, COMM_GET_VALUES, COMM_TERMINAL_CMD, FAULTS,
                       Reader, ask, find_port, frame, read_packet)

CUR_CAP, ERPM_CAP, SEC_CAP = 6.0, 3000, 10.0


DUTY_CAP = 0.15


def openloop(ser, current, erpm, duty=None):
    """Current-vector mode by default. duty= uses foc_openloop_duty instead,
    which applies a VOLTAGE vector and so does not depend on the FOC current
    controller's gains -- the gains come from motor R/L, which are zero on an
    ESC that has never had detection run."""
    if duty is None:
        cmd = f"foc_openloop {current:.2f} {erpm:.0f}"
    else:
        cmd = f"foc_openloop_duty {duty:.3f} {erpm:.0f}"
    ser.write(frame(bytes([COMM_TERMINAL_CMD]) + cmd.encode()))


def keepalive(ser):
    # Without this the firmware's timeout handler releases the motor after ~1 s.
    ser.write(frame(bytes([COMM_ALIVE])))


def sample(ser):
    p = ask(ser, bytes([COMM_GET_VALUES]), COMM_GET_VALUES, timeout=0.4)
    if not p:
        return None
    r = Reader(p[1:])
    try:
        r.i16(); r.i16()
        cur_motor = r.i32() / 100.0
        cur_in = r.i32() / 100.0
        r.i32(); r.i32(); r.i16()
        rpm = r.i32()
        v_in = r.i16() / 10.0
        for _ in range(4):
            r.i32()
        r.i32(); r.i32()
        fault = r.u8()
        return cur_motor, cur_in, rpm, v_in, fault
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", nargs="?")
    ap.add_argument("-c", "--current", type=float, default=2.0, help=f"amps (max {CUR_CAP})")
    ap.add_argument("-e", "--erpm", type=float, default=500, help=f"target erpm (max {ERPM_CAP})")
    ap.add_argument("-s", "--seconds", type=float, default=4.0, help=f"run time (max {SEC_CAP})")
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("-d", "--duty", type=float, default=None,
                    help=f"use voltage mode at this duty 0-{DUTY_CAP} instead of current mode")
    ap.add_argument("--yes", action="store_true", help="required: confirms the wheel is secured")
    a = ap.parse_args()

    if not a.yes:
        sys.exit("Refusing to spin without --yes. Clamp the wheel first.")
    cur = min(abs(a.current), CUR_CAP)
    erpm = min(abs(a.erpm), ERPM_CAP) * (-1 if a.reverse else 1)
    secs = min(abs(a.seconds), SEC_CAP)
    duty = min(abs(a.duty), DUTY_CAP) if a.duty is not None else None

    port = a.port or find_port()
    mode = f"{duty:.3f} duty (VOLTAGE mode)" if duty is not None else f"{cur:.2f} A (current mode)"
    print(f"port {port}   {mode}   ramp to {erpm:+.0f} erpm over {secs:.1f} s\n")

    with serial.Serial(port, 115200, timeout=0.2) as ser:
        time.sleep(0.2)
        pre = sample(ser)
        if pre is None:
            sys.exit("No reply from ESC. Powered on?")
        if pre[4] != 0:
            sys.exit(f"Pre-existing fault: {FAULTS.get(pre[4], pre[4])} -- clear it first.")
        print(f"preflight: {pre[3]:.1f} V, no faults\n")

        t0 = time.time()
        try:
            while True:
                t = time.time() - t0
                if t >= secs:
                    break
                target = erpm * min(1.0, t / max(secs * 0.6, 0.1))   # ramp over first 60%
                openloop(ser, cur, target, duty)
                keepalive(ser)
                s = sample(ser)
                if s:
                    cm, ci, rpm, vin, f = s
                    print(f"  t={t:4.1f}s  cmd={target:+7.0f}  erpm={rpm:+7d}  "
                          f"Imot={cm:5.2f}A  Iin={ci:5.2f}A  {vin:4.1f}V  "
                          f"{FAULTS.get(f, f)}")
                    if f != 0:
                        print("  !! fault -- stopping")
                        break
                time.sleep(0.15)
        except KeyboardInterrupt:
            print("\n  interrupted")
        finally:
            for _ in range(3):
                openloop(ser, 0, 0, 0.0 if duty is not None else None)
                keepalive(ser)
                time.sleep(0.05)
            print("\nstopped (open loop released)")


if __name__ == "__main__":
    main()
