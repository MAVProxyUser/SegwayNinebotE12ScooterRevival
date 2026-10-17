#!/usr/bin/env python3
"""Wait for the ESC, then apply the burnout + regen-braking profile and verify."""
import glob, subprocess, sys, time

MOTOR = [
    ("l_current_max",     "40"),   # phase current -> torque. 0.278 Nm/A
    ("l_abs_current_max", "60"),   # hard trip, must sit above l_current_max
    ("l_in_current_max",  "20"),   # or the 40 A above gets clamped to ~33 A at stall
    ("l_current_min",    "-20"),   # motor brake current
    ("l_in_current_min",  "-6"),   # battery regen ~2.7C into a 2.2Ah LiPo
]
APP = [
    ("app_adc_conf.ctrl_type",      "8"),    # Current No Reverse Brake ADC2
    ("app_adc_conf.voltage2_start", "1.0"),  # float is 0.345-0.405 V; 1.0 gives 600mV margin
]

print("waiting for /dev/cu.usbmodem* (up to 10 min) ...", flush=True)
deadline = time.time() + 600
while time.time() < deadline:
    if glob.glob("/dev/cu.usbmodem*"):
        break
    time.sleep(2)
else:
    sys.exit("ESC never appeared")

time.sleep(2)
print("found it\n", flush=True)

def run(args):
    r = subprocess.run([sys.executable, "vesc_conf.py"] + args,
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip(), flush=True)
    return r.returncode == 0

flat = lambda pairs: [x for p in pairs for x in p]
print("=== motor config ===")
run(["motor", "set"] + flat(MOTOR))
print("\n=== app config ===")
run(["app", "set"] + flat(APP))
print("\n=== final state ===")
run(["motor", "get"] + [n for n, _ in MOTOR] + ["l_battery_cut_start", "l_battery_cut_end"])
run(["app", "get"] + [n for n, _ in APP] + ["app_adc_conf.voltage2_end"])
