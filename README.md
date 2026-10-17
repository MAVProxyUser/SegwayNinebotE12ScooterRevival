# Segway Ninebot Zing E12 — VESC Conversion

Replacing the dead controller on a **Segway Ninebot eKickScooter Zing E12** with a
**Flipsky Mini FSESC6.7 Pro**, driving the stock hub motor, stock thumb throttle and
stock brake lever.

**Status: working.** Throttle, proportional regen braking, and a real road test.

---

## The scooter

[Segway Ninebot eKickScooter Zing E12](https://www.segway.com/ninebot-ekickscooter-zing-e12/e12-specs/)
· [user manual](https://manuals.plus/ninebot/ekickscooter-zing-manual)
· [disassembly video](https://www.youtube.com/watch?v=BBIf_qy6UK4)

| Spec | Value |
|---|---|
| Motor | 150 W, **rear** hub |
| Battery (stock) | 21.6 V nominal, 25.2 V max charge, 55.08 Wh (6S Li-ion) |
| Top speed | 18 km/h |
| Range | 10 km |
| Wheel | 8″ (0.638 m circumference) |
| Motor engages at | ~1.3 mph (≈820 ERPM) — it is a *kick* scooter by design |

**The stock motor has no hall sensors.** Confirmed by inspection and by the absence
of any sensor lead in the loom. Everything here runs sensorless FOC.

### Stock parts referenced

- [Throttle Assembly – E12](https://store.segway.com) — SKU `AB.00.0013.67`, 4 wires: red / black / white / **green**
- [Brake Assembly – E8/E10/E12](https://store.segway.com) — SKU `AB.00.0017.77`
- [Charge Port Fixed Assembly – E8/E10/E12](https://store.segway.com) — SKU `AB.00.0026.03`
- [Throttle-to-battery harness (E10)](https://monsterscooterparts.com/products/throttle-to-battery-wiring-harness-for-the-ninebot-zing-e10-electric-scooter) — 61″, 3 connectors, 4 wires: Black, White, Yellow, split Red

---

## Measured motor constants

All measured on the ESC, not from a datasheet.

```
Resistance        R = 0.1363 Ω
Inductance        L = 352–365 µH
Flux linkage      λ = 12.34–12.47 mWb
Saliency          Lq−Ld = 37.4 µH  (~10% — too low for reliable HFI)
Poles             30  (15 pole pairs)
Torque constant   0.278 N·m per amp of motor current
```

**Pole count was measured, not guessed.** Flux linkage gives a no-load ceiling of
`(V_bus/√3)/λ`; at 15 pole pairs that predicts ~20.6 km/h at 21 V, and the wheel
measured 8,083 ERPM = 20.6 km/h. At 23 pole pairs it would predict 13.4 km/h — below
the scooter's own rated top speed, so physically impossible.

### Speed vs. pack voltage

| Pack | No-load ERPM | Wheel speed |
|---|---|---|
| 21.0 V | ~8,900 | 20.6 km/h |
| 22.2 V | ~9,425 | 24.0 km/h |
| 24.3 V | **9,391 measured** | **24 km/h** |
| 25.2 V | ~10,700 | 27.3 km/h |

Top speed is set by back-EMF against bus voltage. **More current does not raise it** —
only more voltage does.

---

## The controller

[Flipsky Mini FSESC6.7 Pro](https://flipsky.net/products/mini-fsesc6-7-pro-70a) —
VESC 6.6 based, 70 A continuous / 200 A burst, 14–60 V, firmware **6.06**, HW `60`.

### Connectors

| Port | Type | Carries |
|---|---|---|
| **CAN** | JST-GH 1.25 mm, 4-pin | `−, CAL, CAH, 5V` |
| **SENSE** | JST-PH 2.0 mm, 6-pin | `−, H3, H2, H1, TMP, 5V` — unused, no hall sensors |
| **COMM** | JST-PH 2.0 mm | 3.3 V, GND, **ADC1**, **ADC2**, RX/TX |
| **Servo/PPM** | 3-pin `− / 5V / S` next to CAN | RC servo standard |
| **USB** | micro-B | VESC Tool |

**ADC1 = throttle, ADC2 = brake, both powered from 3.3 V** (not 5 V) — per Flipsky's
own ADC documentation. A hall throttle run from 3.3 V scales to fit the ADC input
with no divider.

### Control wiring

| Input | Wire | Pin | Rest | Active |
|---|---|---|---|---|
| Throttle | yellow (harness) = green (throttle) | ADC1 | 0.845 V | 2.59 V |
| Brake | — | ADC2 | 0.35 V | 3.30 V |
| Supply | red | 3.3 V | | |
| Ground | black | GND | | |

The brake lever turned out to be **proportional**, not a switch — it holds steady
intermediate values (~1.59 V) through its travel.

---

## Battery

**6S1P LiPo, 2200 mAh, 50C, 22.2 V nominal, 48.54 Wh**

50C is a *discharge* rating — 110 A available against an 8–20 A draw. Charge
(regen) ratings on hobby LiPo are typically 2–5C, which is why regen is capped at −6 A.

| Per cell | Pack | State |
|---|---|---|
| 4.20 V | 25.2 V | full |
| 3.80 V | 22.8 V | 50% |
| **3.40 V** | **20.4 V** | **cutoff start** |
| **3.30 V** | **19.8 V** | **cutoff end** |

⚠️ **There is no overcharge protection.** `l_max_vin` is 57 V — the ESC's hardware
ceiling, not a battery limit. Regen on a full pack will push cells past 4.2 V and
nothing stops it. Brake lightly on a freshly charged pack, or lower `l_max_vin` to ~26 V
to turn it into a hard overvoltage trip.

---

## Working configuration

### Motor config

| Parameter | Value | Notes |
|---|---|---|
| `l_current_max` | **30 A** | torque. 184 W stall heat ≈ motor's 150 W rating |
| `l_abs_current_max` | 50 A | hard trip |
| `l_in_current_max` | 20 A | battery ceiling (~488 W) |
| `l_current_min` | −20 A | motor brake |
| `l_in_current_min` | −6 A | regen, ~2.7C into 2.2 Ah |
| `l_battery_cut_start` / `_end` | 20.4 / 19.8 V | **LiPo** values, not Li-ion |
| `si_battery_ah` / `_cells` | 2.2 / 6 | |
| `si_motor_poles` | 30 | |
| `foc_sensor_mode` | Sensorless | no halls |
| `foc_openloop_rpm` | 300 | |
| `foc_sl_openloop_time_lock` | 0.0 | see "kick start" below |
| `foc_offsets_cal_mode` | 3 | Calibrate on Boot + **Write Enabled** |

### App config

| Parameter | Value |
|---|---|
| `app_to_use` | 5 (ADC and UART) |
| `app_adc_conf.ctrl_type` | **8** (Current No Reverse Brake ADC2) |
| ADC1 start / end | 0.90 / 2.59 V |
| ADC1 abs min / max | 0.50 / 2.90 V — broken-wire + short-to-rail guard |
| ADC2 start / end | 1.00 / 3.20 V |
| `hyst` | 0.15 |
| `ramp_time_pos` | 0.5 s |
| `multi_esc` | 0 |

**`ctrl_type` must be 8, not 7.** Type 7 ("Brake Button") reads the RX/TX button
inputs, *not* ADC2 — with nothing wired there it sits permanently "braking" and
silently gates the throttle to zero duty. Cost several hours to find.

### Current vs. heat

Stall dissipation is `1.5·I²·R`:

| Motor current | Torque | Force at tyre | Stall heat | vs. 150 W |
|---|---|---|---|---|
| 20 A | 5.6 N·m | 55 N | 82 W | 0.55× — indefinite |
| **30 A** | **8.3 N·m** | **82 N** | **184 W** | **1.2× — chosen** |
| 40 A | 11.1 N·m | 109 N | 327 W | 2.2× — bursts only |

**There is no motor temperature sensor.** The failure mode of sustained overcurrent
is silent, permanent demagnetisation. Hand on the hub is the only instrument.

---

## Kick start

Sensorless FOC has no rotor position at standstill, so the motor needs a push —
which is how the stock scooter works anyway (it engages at ~1.3 mph ≈ 820 ERPM,
almost certainly detected from back-EMF).

Self-starting *is* achievable with `foc_sl_openloop_time_lock = 0.2` (aligns the rotor
before rotating) plus `foc_openloop_rpm = 800`, but it grinds on the way out and was
deliberately reverted. Set `time_lock = 0.0`, `openloop_rpm = 300` for kick-start behaviour.

---

## The bug that cost a week

**Symptom:** both ADC inputs read a hard `0.000 V`, *and* every terminal command
returned nothing. Survived power cycles and a week unplugged.

**Cause:** `FOC Current Offsets` were `0.00 0.00 0.00` instead of ~2048 (the ADC
midpoint). With zero offsets, a normal ~2048 raw reading is interpreted as ≈165 A,
producing a phantom **−72 A at 0% duty, 0 RPM** that instantly tripped
`ABS_OVER_CURRENT`.

**Why it self-perpetuated** — from the firmware's own parameter description:

> *Calibrate on Boot:* "calibration on boot **will fail if there is a fault code active
> during boot** that does not go away within a few seconds."
>
> *Write Enabled:* "When disabled, **the offsets will be ignored when writing the motor
> configuration**."

So: zero offsets → phantom overcurrent at boot → calibration aborts → offsets stay
zero → repeat forever. And `foc_offsets_cal_mode = 1` had *Write Enabled* off, so
writing the known-good offsets back from a config backup was **silently ignored**.

**Fix:** a full **`COMM_DETECT_APPLY_ALL_FOC` (58)** — the detection that rotates the
wheel. `foc_dc_cal` reports "Done!" but does not commit the offsets.

**Dead ends, each disproved rather than assumed:**

| Hypothesis | How it was ruled out |
|---|---|
| `app_to_use` wrong | read from the config blob — correct every time |
| Blown 3.3 V rail | brake read a clean 3.296 V after the failure |
| `voltage_min` guard | reverted twice, no change |
| Config writes stop the app | survived a full power cycle |
| Bad float32_auto encoder | 42/42 firmware-written fields round-trip **byte-exact** |
| Terminal parser bug | raw packet dump — **zero packets**, firmware was silent |

A residual `ABS_OVER_CURRENT` still appears in the log at every boot with
`Tacho: 0, Cycles running: 0` — that is the boot calibration tripping on itself before
the offsets are established. Cosmetic; operation after it is clean.

---

## Tooling

Python, `pyserial` only. These speak the VESC packet protocol directly — no GUI.

| Script | Purpose |
|---|---|
| [`vesc_read.py`](vesc_read.py) | identity, live values, decoded PPM, fault log, terminal commands |
| [`vesc_adc.py`](vesc_adc.py) | watch both ADC channels with min/max capture |
| [`vesc_live.py`](vesc_live.py) | throttle level alongside motor current / duty / ERPM; triggers on throttle |
| [`vesc_conf.py`](vesc_conf.py) | **read and write any config parameter**, motor or app |
| [`vesc_spin.py`](vesc_spin.py) | open-loop spin test — no detection or sensors needed |
| [`restore_config.py`](restore_config.py) | rewrite both configs from `backups/`, one at a time |

`vesc_conf.py` does **not** guess byte offsets. It parses the `<SerOrder>` section and
per-parameter `type`/`vTx` out of VESC Tool's own `parameters_{app,mc}conf.xml` and
reproduces the serializer exactly:

```
CFG_T_DOUBLE(1):  vTx 7 = 2B scaled int16   8 = 4B scaled int32   9 = 4B float32_auto
CFG_T_INT(2):     vTx 1,2 = 1B   3,4 = 2B   5,6 = 4B
ENUM(4) / BOOL(5) / BITFIELD(6):  1B
```

Writes are read-modify-write: fetch the live blob, replace one field's bytes, send it
back byte-identical otherwise. Blob length is validated against the computed layout
(278 B appconf / 483 B mcconf) before anything is written. VESC's non-IEEE754
`float32_auto` codec is implemented and verified byte-exact against firmware-written data.

```bash
python3 vesc_conf.py motor get l_current_max foc_motor_r
python3 vesc_conf.py motor set l_current_max 30 l_abs_current_max 50
python3 vesc_conf.py app   set app_adc_conf.ctrl_type 8
```

### Operational gotchas

- **Power cycle, don't soft reboot.** `COMM_REBOOT` does not clear a latched
  overcurrent state; pulling power does.
- **Don't stack config writes.** Three large flash writes ~1.2 s apart hung the ESC
  hard enough to need a power cycle. `restore_config.py` deliberately settles 4 s.
- **Faults are logged "since start"** — read them *before* power cycling or the
  evidence is gone.
- **Only one process can hold the port.** VESC Tool and these scripts conflict.

---

## What didn't work: MKS Dual FOC V3.2 Plus

Tried first, abandoned. It is a **gimbal motor driver**: Makerbase's own manual
specifies *"Motor phase resistance > 10 Ω"*, 12–24 V, 120 W/channel, <200 KV.
This motor is **0.1363 Ω** — off by ~70×. It also has no Hall support and its current
sensing is wired unidirectional (INA181A2 `REF` tied to GND), so FOC current control
can't be used to compensate.

Useful if you're driving an actual gimbal motor. Repos:
[makerbase-mks/MKS-DUALFOC](https://github.com/makerbase-mks/MKS-DUALFOC) ·
[makerbase-motor/MKS-ESP32FOC](https://github.com/makerbase-motor/MKS-ESP32FOC)

[`sketches/`](sketches) holds the SimpleFOC/ESP32 work from that attempt. **`01_hall_check`
is still useful** — it verifies hall sensors and derives pole pairs using nothing but an
ESP32, no driver board.

---

## Build on macOS (Apple Silicon)

VESC Tool's prebuilt macOS binary is x86_64 (Qt 5.9 static). To get a native arm64 build:

```bash
git clone https://github.com/vedderb/vesc_tool.git && cd vesc_tool
/opt/homebrew/opt/qt@5/bin/qmake -config release "CONFIG += release_macos build_original"
make -j8
```

**Two patches are required:**

1. **arm64.** `vesc_tool.pro` detects Apple Silicon at line ~341 and sets
   `QMAKE_APPLE_DEVICE_ARCHS = arm64`, then the `macx { }` block overwrites it with
   `x86_64 arm64` a few lines later. Against Homebrew's arm64-only Qt the x86_64 slice
   has no Qt to link and you get `Undefined symbols for architecture x86_64`. Set that
   second assignment to `arm64`.

2. **Release, not beta.** Upstream has **no git tags and no GitHub releases** — a plain
   clone lands you on a beta that warns its firmware is incompatible. Releases are marked
   by flipping `VT_IS_TEST_VERSION` in the `.pro`. Build `01d5f109` ("Release 7.00").

Also note VESC Tool connects to FW 6.06 in **"limited mode"** — a command whitelist.
Everything needed here is on it.

---

## Links

**Scooter**
- [Zing E12 specs](https://www.segway.com/ninebot-ekickscooter-zing-e12/e12-specs/) · [manual](https://manuals.plus/ninebot/ekickscooter-zing-manual)
- [Hub motor replacement video](https://www.youtube.com/watch?v=BBIf_qy6UK4)

**Controller**
- [Flipsky Mini FSESC6.7 Pro](https://flipsky.net/products/mini-fsesc6-7-pro-70a)
- [Flipsky ADC throttle/brake wiring](https://flipsky.net/blogs/vesc-tool/how-to-use-adc-for-self-locking-switches-toggle-switches)

**VESC**
- [VESC Tool downloads](https://vesc-project.com/vesc_tool) · [source](https://github.com/vedderb/vesc_tool) · [firmware](https://github.com/vedderb/bldc)
- [VESC Project forum](https://vesc-project.com/)

**Talking to a VESC from code**
- [PyVESC](https://github.com/LiamBindle/PyVESC) · [pyVESC-uart](https://github.com/3mrotaha/pyVESC-uart) · [VescUart (Arduino/ESP32)](https://github.com/SolidGeek/VescUart)

---

## Still open

- **Hall sensors.** The motor has none. Sensored start would need an external sensor
  board; sensorless + kick works fine for a kick scooter.
- **ESP32 integration.** `app_to_use = 5` keeps UART enabled for a SparkFun ESP32
  Thing Plus to talk to the VESC — throttle logic and telemetry without hand-rolling
  commutation.
- **Overvoltage protection.** Consider `l_max_vin ≈ 26 V`.
- **ADC2 pull-down.** Released brake floats ~0.35–0.52 V against a 1.00 V threshold.
  A 10 kΩ to GND would make it immune to noise.
- **Motor temperature sensing.** Nothing on the TMP pin. Any pushing beyond 30 A is
  flying blind.
