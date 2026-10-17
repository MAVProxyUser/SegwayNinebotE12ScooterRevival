#!/usr/bin/env python3
"""
vesc_read.py -- read-only interrogation of a VESC over USB.

Sends nothing that can move the motor. Asks for firmware version, live values,
and the fault log, then prints them.

    python3 vesc_read.py                 # auto-find /dev/cu.usbmodem*
    python3 vesc_read.py /dev/cu.usbmodem3041
    python3 vesc_read.py --term "hw_status"

On macOS always use the /dev/cu.* node, not /dev/tty.* -- the tty device waits
for carrier detect and will just hang.
"""

import glob
import struct
import sys
import time

import serial

COMM_FW_VERSION = 0
COMM_GET_VALUES = 4
COMM_PRINT = 21
COMM_TERMINAL_CMD = 20
COMM_GET_DECODED_PPM = 31
COMM_ALIVE = 30

FAULTS = {
    0: "NONE", 1: "OVER_VOLTAGE", 2: "UNDER_VOLTAGE", 3: "DRV",
    4: "ABS_OVER_CURRENT", 5: "OVER_TEMP_FET", 6: "OVER_TEMP_MOTOR",
    7: "GATE_DRIVER_OVER_VOLTAGE", 8: "GATE_DRIVER_UNDER_VOLTAGE",
    9: "MCU_UNDER_VOLTAGE", 10: "BOOTING_FROM_WATCHDOG_RESET",
    11: "ENCODER_SPI", 12: "ENCODER_SINCOS_BELOW_MIN_AMPLITUDE",
    13: "ENCODER_SINCOS_ABOVE_MAX_AMPLITUDE", 14: "FLASH_CORRUPTION",
    15: "HIGH_OFFSET_CURRENT_SENSOR_1", 16: "HIGH_OFFSET_CURRENT_SENSOR_2",
    17: "HIGH_OFFSET_CURRENT_SENSOR_3", 18: "UNBALANCED_CURRENTS",
}


def find_port():
    found = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not found:
        raise SystemExit("No /dev/cu.usbmodem* found. Is the ESC powered?")
    return found[0]


def crc16(data: bytes) -> int:
    """CRC-CCITT (XMODEM), init 0 -- what the VESC packet layer uses."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def frame(payload: bytes) -> bytes:
    if len(payload) <= 255:
        pkt = bytes([2, len(payload)])
    else:
        pkt = bytes([3, len(payload) >> 8, len(payload) & 0xFF])
    c = crc16(payload)
    return pkt + payload + bytes([c >> 8, c & 0xFF, 3])


def read_packet(ser, timeout=1.5):
    """Return one payload, or None on timeout / bad frame."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        b = ser.read(1)
        if not b:
            continue
        start = b[0]
        if start == 2:
            n = ser.read(1)
            if not n:
                return None
            length = n[0]
        elif start == 3:
            n = ser.read(2)
            if len(n) < 2:
                return None
            length = (n[0] << 8) | n[1]
        else:
            continue  # resync
        body = ser.read(length + 3)
        if len(body) < length + 3:
            return None
        payload, crc_hi, crc_lo, stop = body[:length], body[length], body[length + 1], body[length + 2]
        if stop != 3 or crc16(payload) != (crc_hi << 8) | crc_lo:
            continue
        return payload
    return None


class Reader:
    def __init__(self, data):
        self.d, self.i = data, 0

    def _take(self, n):
        v = self.d[self.i:self.i + n]
        self.i += n
        return v

    def i8(self):   return struct.unpack(">b", self._take(1))[0]
    def u8(self):   return self._take(1)[0]
    def i16(self):  return struct.unpack(">h", self._take(2))[0]
    def i32(self):  return struct.unpack(">i", self._take(4))[0]
    def left(self): return len(self.d) - self.i


def ask(ser, payload, want_id, timeout=1.5):
    ser.reset_input_buffer()
    ser.write(frame(payload))
    deadline = time.time() + timeout
    while time.time() < deadline:
        p = read_packet(ser, timeout=deadline - time.time())
        if p and p[0] == want_id:
            return p
    return None


def show_fw(ser):
    p = ask(ser, bytes([COMM_FW_VERSION]), COMM_FW_VERSION)
    if not p:
        print("  no response to FW_VERSION")
        return False
    major, minor = p[1], p[2]
    rest = p[3:]
    end = rest.find(b"\x00")
    hw = rest[:end].decode("ascii", "replace") if end >= 0 else "?"
    uuid = rest[end + 1:end + 13].hex(":") if end >= 0 and len(rest) >= end + 13 else "?"
    # VESC convention zero-pads the minor: major=6, minor=6 is "6.06", not "6.6"
    print(f"  firmware   : {major}.{minor:02d}")
    print(f"  hardware   : {hw}")
    print(f"  uuid       : {uuid}")
    return True


def show_values(ser):
    p = ask(ser, bytes([COMM_GET_VALUES]), COMM_GET_VALUES)
    if not p:
        print("  no response to GET_VALUES")
        return
    r = Reader(p[1:])
    try:
        temp_fet   = r.i16() / 10.0
        temp_motor = r.i16() / 10.0
        cur_motor  = r.i32() / 100.0
        cur_in     = r.i32() / 100.0
        r.i32(); r.i32()                      # id, iq
        duty       = r.i16() / 1000.0
        rpm        = r.i32()
        v_in       = r.i16() / 10.0
        r.i32(); r.i32(); r.i32(); r.i32()    # Ah, Ah charged, Wh, Wh charged
        tach       = r.i32()
        tach_abs   = r.i32()
        fault      = r.u8()
    except (struct.error, IndexError):
        print("  short GET_VALUES reply -- firmware layout differs, use VESC Tool")
        return

    print(f"  input volt : {v_in:.1f} V")
    print(f"  FET temp   : {temp_fet:.1f} C")
    print(f"  motor temp : {temp_motor:.1f} C   (meaningless with no temp sensor)")
    print(f"  motor curr : {cur_motor:.2f} A")
    print(f"  input curr : {cur_in:.2f} A")
    print(f"  duty       : {duty * 100:.1f} %")
    print(f"  erpm       : {rpm}")
    print(f"  tachometer : {tach}  (abs {tach_abs})")
    print(f"  fault      : {FAULTS.get(fault, f'code {fault}')}")


def show_ppm(ser):
    """Is the PPM/servo signal actually being decoded? Read-only."""
    p = ask(ser, bytes([COMM_GET_DECODED_PPM]), COMM_GET_DECODED_PPM)
    if not p:
        print("  no response")
        return
    r = Reader(p[1:])
    level = r.i32() / 1000000.0
    # Firmware sends pulse length in ms scaled by 1e6, so raw/1000 = microseconds.
    # (My first version chained multiplies that cancelled out and printed the raw value.)
    pulse_us = r.i32() / 1000.0
    print(f"  decoded level : {level:+.3f}   (-1..+1)")
    print(f"  last pulse    : {pulse_us:.0f} us")
    if pulse_us < 1:
        print("  -> nothing decoded.")
        print("     If the tester IS powered and connected: the PPM app is disabled.")
        print("     The servo decoder only runs while the app is active, so this")
        print("     reads 0 even with perfect wiring. Enable PPM in VESC Tool's")
        print("     Input Setup Wizard, then re-run to check the wiring itself.")
        print("     If the tester is OFF: this reading tells you nothing.")
    else:
        print("  -> signal IS being decoded (a servo tester gives ~1000-2000 us),")
        print("     so the PPM app is enabled and the wiring is good.")


def terminal(ser, cmd):
    ser.reset_input_buffer()
    ser.write(frame(bytes([COMM_TERMINAL_CMD]) + cmd.encode()))
    deadline, got = time.time() + 2.0, False
    while time.time() < deadline:
        p = read_packet(ser, timeout=deadline - time.time())
        if p and p[0] == COMM_PRINT:
            got = True
            print("  " + p[1:].decode("ascii", "replace").rstrip())
    if not got:
        print("  (no output)")


def main():
    args = [a for a in sys.argv[1:]]
    extra_cmds = []
    while "--term" in args:
        i = args.index("--term")
        extra_cmds.append(args[i + 1])
        del args[i:i + 2]

    port = args[0] if args else None
    if not port:
        found = sorted(glob.glob("/dev/cu.usbmodem*"))
        if not found:
            sys.exit("No /dev/cu.usbmodem* found. Is the ESC powered? USB needs the "
                     "ESC running off the battery/supply, not USB alone.")
        port = found[0]
    if "/tty." in port:
        print(f"warning: {port} is the tty node and may hang; prefer the cu. node\n")

    print(f"port: {port}\n")
    with serial.Serial(port, 115200, timeout=0.2) as ser:
        time.sleep(0.2)
        print("[ identity ]")
        if not show_fw(ser):
            sys.exit("\nNo reply. Check the ESC is powered on, and that nothing else "
                     "(VESC Tool) is holding the port.")
        print("\n[ live values ]")
        show_values(ser)
        print("\n[ ppm / servo input ]")
        show_ppm(ser)
        print("\n[ faults ]")
        terminal(ser, "faults")
        for c in extra_cmds:
            print(f"\n[ {c} ]")
            terminal(ser, c)


if __name__ == "__main__":
    main()
