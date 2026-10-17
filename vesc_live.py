#!/usr/bin/env python3
"""Watch throttle level and what the motor actually does, side by side."""
import sys, time, serial
from vesc_read import frame, read_packet, Reader, ask, find_port, FAULTS, COMM_GET_VALUES

COMM_GET_DECODED_ADC = 32

def vals(ser):
    p = ask(ser, bytes([COMM_GET_VALUES]), COMM_GET_VALUES, timeout=0.4)
    if not p: return None
    r = Reader(p[1:])
    r.i16(); r.i16()
    im = r.i32()/100.0; ii = r.i32()/100.0
    r.i32(); r.i32()
    duty = r.i16()/1000.0
    rpm = r.i32(); vin = r.i16()/10.0
    for _ in range(4): r.i32()
    r.i32(); r.i32()
    return im, ii, duty, rpm, vin, r.u8()

def adc(ser):
    p = ask(ser, bytes([COMM_GET_DECODED_ADC]), COMM_GET_DECODED_ADC, timeout=0.4)
    if not p: return None
    r = Reader(p[1:])
    l1 = r.i32()/1e6; v1 = r.i32()/1e6
    return l1, v1

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 12
with serial.Serial(find_port(), 115200, timeout=0.2) as ser:
    time.sleep(0.2)
    # wait for the throttle to actually be applied, so timing doesn't matter
    print("  waiting for throttle (up to 60s) ...", flush=True)
    wait_end = time.time() + 300
    while time.time() < wait_end:
        a = adc(ser)
        if a and a[0] > 0.05:
            print(f"  triggered at level {a[0]:.3f}\n", flush=True)
            break
        time.sleep(0.1)
    else:
        print("  never saw throttle above 5% in 300s\n")
    t0 = time.time()
    while time.time() - t0 < secs:
        a = adc(ser); v = vals(ser)
        if a and v:
            l1, v1 = a; im, ii, duty, rpm, vin, f = v
            print(f"  thr {v1:5.3f}V lvl {l1:5.3f} | Imot {im:6.2f}A  Iin {ii:5.2f}A  "
                  f"duty {duty*100:6.1f}%  erpm {rpm:6d}  {vin:4.1f}V  {FAULTS.get(f,f)}", flush=True)
        time.sleep(0.2)
