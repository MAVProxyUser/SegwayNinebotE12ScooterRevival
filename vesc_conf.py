#!/usr/bin/env python3
"""
vesc_conf.py -- read and modify VESC app/motor configuration over USB.

Does NOT guess byte offsets. It parses the firmware's own parameter XML that
VESC Tool ships (res/config/<fw>/parameters_appconf.xml), which contains the
exact <SerOrder> plus each parameter's type and transmit width, and reproduces
VESC Tool's serializer:

    CFG_T_DOUBLE(1):  vTx 7=2B(scaled16)  8=4B  9=4B(auto)
    CFG_T_INT(2):     vTx 1,2=1B   3,4=2B   5,6=4B
    CFG_T_ENUM(4) / BOOL(5) / BITFIELD(6):  1B

Writes are read-modify-write: the live blob is fetched, one field's bytes are
replaced, and the rest is sent back byte-identical. Nothing is re-encoded, so
fields this script can't decode (VESC's custom float32_auto) pass through intact.

    python3 vesc_conf.py get
    python3 vesc_conf.py get app_to_use
    python3 vesc_conf.py set app_to_use 5
"""
import re, sys, time, struct, glob, os
import serial
from vesc_read import frame, read_packet, find_port

COMM_GET_APPCONF, COMM_SET_APPCONF = 17, 16
COMM_GET_MCCONF,  COMM_SET_MCCONF  = 14, 13

def _xml(kind):
    hits = sorted(glob.glob(f"vesc_tool/res/config/*/parameters_{kind}.xml"))
    pick = [h for h in hits if "6.06" in h] or hits
    if not pick:
        sys.exit(f"parameters_{kind}.xml not found under vesc_tool/res/config/")
    return pick[0]

CONFIGS = {
    "app":   dict(xml=_xml("appconf"), get=COMM_GET_APPCONF, set=COMM_SET_APPCONF),
    "motor": dict(xml=_xml("mcconf"),  get=COMM_GET_MCCONF,  set=COMM_SET_MCCONF),
}


def f32auto_decode(raw):
    """VESC's buffer_get_float32_auto -- not IEEE754."""
    import math
    res = int.from_bytes(raw, "big")
    e = (res >> 23) & 0xFF
    sig_i = res & 0x7FFFFF
    neg = bool(res & (1 << 31))
    sig = 0.0
    if e != 0 or sig_i != 0:
        sig = sig_i / (8388608.0 * 2.0) + 0.5
        e -= 126
    if neg:
        sig = -sig
    return math.ldexp(sig, e)


def f32auto_encode(number):
    """VESC's buffer_append_float32_auto."""
    import math
    sig, e = math.frexp(float(number))
    sig_abs = abs(sig)
    sig_i = 0
    if sig_abs >= 0.5:
        sig_i = int((sig_abs - 0.5) * 2.0 * 8388608.0)
        e += 126
    res = ((e & 0xFF) << 23) | (sig_i & 0x7FFFFF)
    if sig < 0:
        res |= 1 << 31
    return res.to_bytes(4, "big")

WIDTH_INT = {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4}
WIDTH_DBL = {7: 2, 8: 4, 9: 4}


def load_layout(xmlpath):
    x = open(xmlpath, encoding="utf-8", errors="replace").read()
    order = re.findall(r"<ser>(.*?)</ser>", re.search(r"<SerOrder>(.*?)</SerOrder>", x, re.S).group(1))
    layout, off = [], 4          # 4-byte signature first
    for name in order:
        blk = re.search(rf"<{re.escape(name)}>(.*?)</{re.escape(name)}>", x, re.S)
        if not blk:
            sys.exit(f"param {name} in SerOrder but not defined")
        b = blk.group(1)
        t = int(re.search(r"<type>(\d+)</type>", b).group(1))
        vtx_m = re.search(r"<vTx>(\d+)</vTx>", b)
        vtx = int(vtx_m.group(1)) if vtx_m else 0
        if t in (4, 5, 6):
            w, kind = 1, "int"
        elif t == 2:
            w, kind = WIDTH_INT.get(vtx, 0), "int"
        elif t == 1:
            w, kind = WIDTH_DBL.get(vtx, 0), "dbl"
        else:
            w, kind = 0, "skip"
        if w == 0:
            sys.exit(f"cannot size {name} (type {t}, vTx {vtx})")
        enums = re.findall(r"<enumNames>(.*?)</enumNames>", b)
        sc = re.search(r"<vTxDoubleScale>([\d.eE+-]+)</vTxDoubleScale>", b)
        layout.append(dict(name=name, off=off, w=w, kind=kind, type=t, vtx=vtx,
                           enums=enums, scale=float(sc.group(1)) if sc else 1.0))
        off += w
    return layout, off


def xfer(payload, want, timeout=3.0):
    port = find_port()
    with serial.Serial(port, 115200, timeout=0.3) as ser:
        time.sleep(0.2); ser.reset_input_buffer()
        ser.write(frame(payload))
        end = time.time() + timeout
        while time.time() < end:
            p = read_packet(ser, timeout=max(0.1, end - time.time()))
            if p and (want is None or p[0] == want):
                return p
    return None


def get_blob(cfg):
    p = xfer(bytes([cfg["get"]]), cfg["get"])
    if not p:
        sys.exit("no config response (is VESC Tool holding the port?)")
    return bytearray(p[1:])


def decode(blob, f):
    raw = blob[f["off"]:f["off"] + f["w"]]
    if f["kind"] == "int":
        return int.from_bytes(raw, "big", signed=(f["type"] == 2 and f.get("vtx") in (2, 4, 6)))
    if f["kind"] == "dbl" and f["vtx"] in (7, 8):      # scaled int16 / int32
        return int.from_bytes(raw, "big", signed=True) / f["scale"]
    if f["kind"] == "dbl" and f["vtx"] == 9:
        return f32auto_decode(raw)
    return None


def encode(f, val):
    if f["kind"] == "int":
        return int(val).to_bytes(f["w"], "big")
    if f["kind"] == "dbl" and f["vtx"] in (7, 8):
        return int(round(float(val) * f["scale"])).to_bytes(f["w"], "big", signed=True)
    if f["kind"] == "dbl" and f["vtx"] == 9:
        return f32auto_encode(val)
    raise SystemExit(f"{f['name']}: unsupported encoding (vTx {f['vtx']})")


def main():
    args = sys.argv[1:]
    which = "app"
    if args and args[0] in CONFIGS:
        which = args.pop(0)
    cfg = CONFIGS[which]
    layout, total = load_layout(cfg["xml"])
    byname = {f["name"]: f for f in layout}
    cmd = args[0] if args else "get"
    sys.argv = ["x"] + args

    if cmd == "layout":
        for f in layout[:25]:
            print(f"  {f['off']:4d} +{f['w']}  {f['name']}")
        print(f"  ... total {total} bytes")
        return

    blob = get_blob(cfg)
    sig = int.from_bytes(blob[0:4], "big")
    ok = len(blob) == total
    print(f"blob {len(blob)} bytes (layout expects {total}) "
          f"{'MATCH' if ok else '*** MISMATCH — wrong fw XML ***'}   signature 0x{sig:08x}\n")
    if not ok:
        sys.exit("refusing to continue with a mismatched layout")

    if cmd == "dumpall":
        pat = sys.argv[2] if len(sys.argv) > 2 else ""
        for f in layout:
            if pat and pat not in f["name"]:
                continue
            v = decode(blob, f)
            lbl = f["enums"][v] if f["enums"] and isinstance(v, int) and v < len(f["enums"]) else ""
            print(f"  {f['name']:34s} = {v}  {lbl}")
        return

    if cmd == "get":
        want = sys.argv[2:] or ["controller_id", "app_to_use", "app_adc_conf.ctrl_type",
                                "app_ppm_conf.ctrl_type", "permanent_uart_enabled"]
        for n in want:
            f = byname.get(n)
            if not f:
                print(f"  {n}: not a parameter"); continue
            v = decode(blob, f)
            lbl = f["enums"][v] if f["enums"] and v is not None and v < len(f["enums"]) else ""
            print(f"  {n:28s} = {v}  {lbl}")
        return

    if cmd == "set":
        pairs = sys.argv[2:]
        if len(pairs) % 2:
            sys.exit("need name/value pairs")
        for name, val in zip(pairs[::2], pairs[1::2]):
            f = byname.get(name) or sys.exit(f"unknown parameter {name}")
            old = decode(blob, f)
            blob[f["off"]:f["off"] + f["w"]] = encode(f, val)
            print(f"  {name}: {old} -> {val}  (offset {f['off']}, {f['w']}B)")
        f = byname[pairs[0]]; val = float(pairs[1])
        r = xfer(bytes([cfg["set"]]) + bytes(blob), None, timeout=3.0)
        time.sleep(0.5)
        if which == "app":
            print("  NOTE: writing appconf stops the ADC/PPM input app. A soft\n"
                  "  COMM_REBOOT does not reliably restart it -- POWER CYCLE the\n"
                  "  ESC before trusting any input reading.")
        nb = get_blob(cfg)
        ok = True
        for name, v in zip(pairs[::2], pairs[1::2]):
            ff = byname[name]; got = decode(nb, ff)
            good = abs(float(got) - float(v)) < (1.0 / ff["scale"] if ff["kind"] == "dbl" else 0.5)
            ok &= good
            print(f"  readback {name:30s} = {got}  {'OK' if good else '*** FAILED ***'}")
        return

    sys.exit(__doc__)


if __name__ == "__main__":
    main()
