#!/usr/bin/env python3
"""
vesc_adc.py -- watch the VESC's decoded ADC inputs (throttle / brake) live.

Read-only. Polls COMM_GET_DECODED_ADC and reports both channels plus the
min/max seen over the run, so you can sweep a throttle and squeeze a brake
and see the usable range.

    python3 vesc_adc.py            # 20 s
    python3 vesc_adc.py 30         # 30 s

NOTE: the ADC app must be enabled (App to Use = "ADC" or "ADC and UART").
With the PPM app selected these will read zero no matter how good the wiring.
"""
import sys, time, serial
from vesc_read import frame, read_packet, Reader, ask, find_port

COMM_GET_DECODED_ADC = 32


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
    port = find_port()
    print(f"port {port}   watching {secs:.0f}s — sweep the throttle, squeeze the brake\n")
    lo1 = lo2 = 9e9
    hi1 = hi2 = -9e9
    first = True
    with serial.Serial(port, 115200, timeout=0.2) as ser:
        time.sleep(0.2)
        t0 = time.time()
        while time.time() - t0 < secs:
            p = ask(ser, bytes([COMM_GET_DECODED_ADC]), COMM_GET_DECODED_ADC, timeout=0.4)
            if not p:
                print("  no reply"); time.sleep(0.2); continue
            r = Reader(p[1:])
            lvl1 = r.i32() / 1e6
            v1   = r.i32() / 1e6
            lvl2 = r.i32() / 1e6
            v2   = r.i32() / 1e6
            if first:
                print(f"  (raw payload {len(p)-1} bytes)")
                first = False
            lo1, hi1 = min(lo1, v1), max(hi1, v1)
            lo2, hi2 = min(lo2, v2), max(hi2, v2)
            print(f"  ADC1 {v1:6.3f} V (lvl {lvl1:+.3f})   "
                  f"ADC2 {v2:6.3f} V (lvl {lvl2:+.3f})", flush=True)
            time.sleep(0.15)
    print(f"\n  ADC1 range: {lo1:.3f} .. {hi1:.3f} V   (span {hi1-lo1:.3f})")
    print(f"  ADC2 range: {lo2:.3f} .. {hi2:.3f} V   (span {hi2-lo2:.3f})")
    if hi1 - lo1 < 0.05 and hi2 - lo2 < 0.05:
        print("\n  Nothing moved. Either the ADC app is not enabled "
              "(App to Use must be ADC / ADC and UART), or the signal "
              "wire is not on ADC1.")


if __name__ == "__main__":
    main()
