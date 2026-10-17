# Flipsky Mini FSESC6.7 Pro — setup for the E12 hub motor

## Why the servo tester did nothing

Your CCPM tester is fine, and the signal type is right — VESC's "PPM" app is actually
standard servo PWM despite the name. The problem is that a VESC is not a hobby ESC.
A hobby ESC arms and runs out of the box; a VESC ships inert and does nothing until
it is configured. Any **one** of these is enough to produce exactly what you saw:

1. **No motor configuration.** A fresh VESC has no motor parameters at all. Until you
   run motor detection, there is nothing for a throttle signal to command.
2. **The PPM app is not enabled by default.** It has to be turned on in
   `App Settings → General → App to Use → PPM` (or via the Input Setup Wizard),
   then **the VESC must be rebooted** for it to take effect.
3. **PPM is uncalibrated.** Even enabled, the VESC doesn't know your tester's pulse
   range until you map it.
4. **Safe start.** Once working, the motor will refuse to start unless the PPM input
   was at its minimum when the VESC powered up. A tester left mid-throttle at
   power-on looks exactly like a dead ESC.

Fix all four by running the wizards below. But do the motor first — PPM can't do
anything until the motor is detected.

---

## The thing to be careful about: this ESC is ~10× your motor

| | Mini FSESC6.7 Pro | E12 motor / pack |
|---|---|---|
| Current | **70 A cont. / 200 A burst** | ~7 A at rated power |
| Voltage | 14–60 V (4–12S safe) | 21.6 V nom, 25.2 V max (6S) |
| Power | kilowatts | 150 W |

The voltage match is good — 6S sits comfortably in range, and your low-voltage cutoff
will be well above the ESC's 14 V minimum. The current match is not. **VESC default
current limits will destroy this motor and pack without complaining.** Setting the
limits below is not optional tuning, it's the main configuration job.

---

## Getting VESC Tool on macOS

**It runs on macOS and it's free.** From the project's own README: the stable binary is
available for Linux, Windows, macOS, Android and iOS, and *"all binaries can be
downloaded free-of-charge for all platforms except for iOS"* (iOS is App Store only).

Download from **<https://vesc-project.com/vesc_tool>**. The store lists tiers from
Free (€0) up to Platinum (€20) — the paid ones are a way to support Vedder's
development. Grab the free one to start.

### Two macOS-specific snags

1. **Gatekeeper.** The app isn't notarized, so macOS will refuse to open it on first
   try. Either strip the quarantine flag:

   ```
   xattr -dr com.apple.quarantine /Applications/vesc_tool.app
   ```

   or go to System Settings → Privacy & Security and hit "Open Anyway" after the
   first blocked launch.

2. **Apple Silicon.** Upstream's `build_macos` script builds against a static Qt 5.9,
   which means the official binary is likely x86_64 and will run under Rosetta. If
   Rosetta isn't installed yet:

   ```
   softwareupdate --install-rosetta
   ```

   If the prebuilt app misbehaves, build native arm64 from source — see below.

### USB connection

The ESC has a **micro-USB** port (a micro-B cable is in the box). Your Mac is USB-C,
so you need a USB-C → micro-B cable or an adapter.

It enumerates as a standard USB CDC device, so **macOS needs no driver** — it appears
as `/dev/cu.usbmodem*`. (Unlike the CH340-based boards that need a kext.)

> ### ⚠️ The ESC must be powered from the battery for USB to work
>
> I told you earlier that USB alone powers the logic side. That's true of VESC 4.12,
> but **not** of this board — Flipsky's own instructions are to power the ESC up
> first, *then* connect USB. On VESC 6 hardware the 3.3 V rail comes off a
> battery-fed buck converter, not USB VBUS.
>
> So: bench supply on and ESC powered **before** you plug in USB, or no serial port
> appears and it looks exactly like a dead ESC — the same failure mode that got you
> with the servo tester.

If no port shows up after that, suspect the cable — plenty of micro-USB cables are
charge-only.

---

## "Can we RE it and make something compatible?"

You don't have to, and it would be wasted effort — **none of this is closed**:

- **VESC Tool is GPL-3.0**, full source at <https://github.com/vedderb/vesc_tool>,
  with a `build_macos` script in the repo. Needs Qt5. Building from source is the
  fallback if the prebuilt binary won't run on your machine, and gets you a native
  arm64 build.
- **The firmware is open too** (`vedderb/bldc`), so the serial protocol is documented
  in readable source rather than something you'd have to sniff off the wire.

If you want to talk to the ESC from your own code anyway — and this is the clean way
to get the ESP32 Thing Plus back into this project — the protocol already has
libraries:

| Library | Use |
|---|---|
| [PyVESC](https://github.com/LiamBindle/PyVESC) | Python, the long-standing implementation |
| [pyVESC-uart](https://github.com/3mrotaha/pyVESC-uart) | Python, newer; RPM/duty/current control, telemetry, PID config |
| [VescUart](https://github.com/SolidGeek/VescUart) | Arduino/ESP32 — this is the one for the Thing Plus |

The architecture that gets you what you originally wanted: **VESC does commutation and
current control, ESP32 does throttle logic, telemetry and whatever else over UART.**
You skip writing a commutation loop entirely, which is the part that was never going
to be worth hand-rolling.

---

## What you can do over USB



With the ESC powered and USB connected you can:

- Connect, read and write the entire configuration
- Check and update firmware
- Read realtime data and the fault log (Terminal → `faults`)
- Run motor detection (this spins the motor — it is itself a real functional test)
- Run hall sensor detection
- **Drive the motor directly from VESC Tool, no remote required.** This is the
  "proper interface" you're after: the `I`, `D` and `RPM` fields at the
  **bottom-left** of the window, plus the **keyboard control toggle on the right
  sidebar**. With keyboard control on, left/right arrows run current mode limited to
  the `I` value; up/down arrows run duty mode using `D`. Start at the smallest
  values the fields will take.

You never need the servo tester to verify the ESC works.

### Other ways in, if USB is inconvenient

| Method | What it needs | Good for |
|---|---|---|
| **USB** | micro-B cable, ESC powered | everything; use this on the bench |
| **UART** | the comm port + a USB-serial adapter, or your ESP32 | scripted control, embedding |
| **CAN** | a second VESC on the bus | CAN forwarding — configure other VESCs through one connection; also avoids USB ground loops |
| **BLE** | an nRF51/nRF52 module on the UART port (Flipsky nRF, Metr Pro, Trampa dongle) flashed with VESC-compatible firmware | wireless tuning; VESC Tool has a BLE tab on the Connection page |
| **TCP/UDP** | the Android app's bridge function, or a Pi running a bridge | reaching the ESC over a network |

There is no Bluetooth on the board itself — BLE needs the add-on module.

**You do not need the iOS or Android app.** Those exist for field tuning over
Bluetooth and are the paid builds; on a Mac with a USB cable the desktop tool does
strictly more. (An Apple Silicon Mac *can* sometimes run the iOS app, but it would
still need BLE plus the nRF module, so there's no reason to.)

---

## Bench setup

- Wheel **off the ground and clamped**. 70 A of ESC on a scooter wheel deserves respect.
- Motor phases to the three ESC phase outputs. Order doesn't matter — detection sorts it out.
- Hall connector to the sensor port (JST PH 2.0, 6-pin: GND, 5V, H1, H2, H3, TEMP).
  The E12 connector is probably 5-wire, so you'll need an adapter; leave TEMP unused.
- **Set "Motor Temperature Sensor Type" to disabled** since you have no temp sensor
  on that pin, or the ESC may derate or fault on a bogus reading.
- Power: bench supply at ~20 V. **Power the ESC up before plugging in USB** (see above).
  Running the Mac on battery rather than its charger avoids a ground loop through the
  USB shield. **If you're on a bench supply, set
  `Battery Current Max Regen` to about −1 A first.** A bench supply cannot absorb
  regen current, and braking into one causes an overvoltage fault or worse. The
  battery can absorb it; a power supply can't.

---

## Measured motor parameters (E12 hub motor, 2026-10-06)

Taken from the ESC itself via `measure_res` / `measure_ind`:

| | Value |
|---|---|
| Resistance | **0.364 Ω** |
| Inductance | **273.28 µH** |
| ld_lq_diff | 111.84 µH (real saliency — healthy magnets) |

The motor is connected and electrically sound. Detection will re-measure these;
if the wizard reports wildly different numbers, suspect the wiring, not the motor.

Note: `measure_res` takes several seconds to return. A reader that gives up early
sees only "Measuring resistance..." and looks like a failure.

## Order of operations

Firmware first — **a firmware update wipes all settings**, so doing it later costs you
the whole configuration.

1. **Connect over USB**, check the firmware version. Let VESC Tool auto-detect the
   hardware; don't override it. Only update if there's a reason to.
2. **Motor Setup Wizard** (Welcome & Wizards) → FOC → sensored.
   - Motor poles = **2 × pole pairs** from sketch 01. VESC wants poles, not pairs.
   - When it asks for detection current, give it something small — a few amps. The
     default is sized for much bigger motors than this.
   - It measures resistance, inductance and flux linkage, then detects the hall table.
     If hall detection fails, your hall wiring or the sensors are the problem —
     sketch 01 will tell you which.
3. **Set the current limits** (Motor Settings → General → Current):

   | Setting | Value | Why |
   |---|---|---|
   | Motor Current Max | 15 A | motor current exceeds battery current at low duty |
   | Motor Current Max Brake | −10 A | |
   | Battery Current Max | 8 A | ~150 W at 21.6 V is 7 A |
   | Battery Current Max Regen | −3 A (or −1 A on a bench supply) | small pack |
   | Absolute Max Current | 25 A | hard trip |

4. **Set the voltage cutoffs** (Motor Settings → General → Voltage):
   Cutoff Start **19.2 V** (3.2 V/cell), Cutoff End **18.0 V** (3.0 V/cell) for 6S li-ion.
   Both are far above the ESC's 14 V floor.
5. **Write the config**, then bench test with keyboard control. Watch current draw and
   temperature. A 150 W motor spinning free should pull well under an amp.
6. **Only then** do the Input Setup Wizard for PPM, if you still want the tester or a
   throttle. Remember the reboot and the safe-start rule.

---

## Quick read-only check without the GUI

[`vesc_read.py`](vesc_read.py) in this repo talks the VESC packet protocol directly
over USB and prints identity, live telemetry and the fault log. It sends nothing that
can move the motor.

```
python3 vesc_read.py                      # auto-finds /dev/cu.usbmodem*
python3 vesc_read.py --term "hw_status"   # any read-only terminal command
```

**It does not read the motor/app configuration.** Those are packed binary blobs whose
layout is defined per-firmware by VESC's config generator, and VESC Tool decodes them
with bundled XML. For actual parameters, use the GUI.

### Terminal commands that are NOT read-only

`help` lists several that energize or spin the motor — don't run them casually:

| Command | What it does |
|---|---|
| `param_detect` | spins the motor up in open loop |
| `measure_res` | **locks the rotor with DC current** — heats the winding |
| `measure_ind` | pulses voltage into the windings |
| `measure_linkage` | spins the motor |
| `foc_encoder_detect` | rotates the motor at 1 Hz open loop |

Wheel off the ground and current limits set before any of them.

## Motor Setup Wizard — values for the E12

Do the motor **before** PPM. A throttle input can't command anything until the
motor is configured, and that ordering also keeps you from debugging two unknowns
at once.

### What we know vs. what you must check

| Parameter | Value | Confidence |
|---|---|---|
| Motor type | **FOC** | certain |
| Sensor mode | **Sensorless for now** | halls exist on the motor but are NOT wired to the ESC yet |
| Resistance | 0.364 Ω | **measured on this ESC** |
| Inductance | 273 µH | **measured on this ESC** |
| Battery | 6S li-ion, 21.6 V nom / 25.2 V max | Segway spec — verify on the pack label |
| Capacity | ~2.55 Ah (55.08 Wh ÷ 21.6 V) | derived from spec |
| Motor poles | **UNKNOWN — see below** | guess 30 (15 pole pairs) to start |
| Wheel diameter | **measure your tire** | display only, no effect on control |

### Wizard steps

0. **Sensor mode: choose Sensorless.** The halls aren't connected to the sensor
   port yet, so there is nothing to detect. Detection itself is sensorless anyway —
   R, L and flux linkage are all measured without sensors — so nothing is lost by
   starting here. See "Adding the hall sensors later" below.
1. **Motor type:** FOC.
2. **Battery:** Li-ion, **6** cells in series, **2.55 Ah**. The wizard derives the
   cutoffs; confirm they land near **19.2 V start / 18.0 V end** (3.2 / 3.0 V per
   cell). Both are far above the ESC's 14 V floor.
3. **Current limits** — the most important screen, because this is a 70 A ESC on a
   150 W motor and the defaults will cook it:

   | Setting | Value | Reasoning |
   |---|---|---|
   | Motor Current Max | **12–15 A** | peak starting torque only; 15 A through 0.364 Ω is 82 W of heat per phase, fine in bursts, not continuously |
   | Motor Current Max Brake | **−10 A** | |
   | Battery Current Max | **8 A** | 150 W ÷ 21.6 V ≈ 7 A — this is what caps sustained power |
   | Battery Current Max Regen | **−3 A** | small pack; use **−1 A** on a bench supply, which cannot absorb regen |
   | Absolute Max Current | **25 A** | hard trip |

   Battery current max is the real protection. Motor current can legitimately
   exceed it at low duty, which is why the two numbers differ.
4. **Run detection.** It re-measures R and L — **expect ~0.364 Ω and ~273 µH.**
   Numbers close to those mean detection is healthy; wildly different means check
   wiring before going further. It then measures flux linkage, which spins the motor.
5. **Skip hall/encoder detection** — nothing is connected to the sensor port.
6. **Disable the motor temperature sensor** — the TEMP pin is unused, and it
   currently reads about −80 °C.

### Adding the hall sensors later

Sensorless FOC is fine on the bench with the wheel free. It is **not** fine on the
road: sensorless has little to no torque from a standstill, so a scooter will cog,
stutter or refuse to start under a rider. Halls fix exactly that.

What you need: the VESC sensor port is **JST PH 2.0, 6-pin** — GND, 5 V, H1, H2, H3,
TEMP. The E12's hall connector is 5-wire (no temp), so you need an adapter cable.
Leave TEMP unconnected and keep the temp sensor disabled.

Once wired, you do **not** redo the whole wizard — just run hall detection and switch
the sensor mode to Hall. The R/L/flux-linkage numbers you already have stay valid.

### Determining the pole count

Nothing in detection needs it — poles only affect displayed RPM and speed. So set
**30 poles (15 pole pairs)** as a starting guess, get it running, then measure:

```
pole_pairs = ERPM / actual_wheel_RPM
```

Run at a steady speed, read ERPM in VESC Tool, and count real wheel revolutions
(phone slow-mo, or a mark on the tire). Round to a whole number and set
poles = 2 × that. `sketches/01_hall_check` gives the same answer from hall
transitions ÷ 6 if you'd rather wire the halls to the ESP32.

## Enabling the PPM app

The Input Setup Wizard does all of this guided, which is easier than the manual
route below — but the manual steps are worth knowing because of the reboot.

1. **App Settings → General → App to Use → `PPM and UART`.**
   Not plain `PPM` — UART is how the ESP32 Thing Plus talks to the VESC later, and
   picking it now saves redoing this.
2. **Write App Configuration.**
3. **Reboot the VESC.** The app change does not take effect until you do. This is
   the step people skip.
4. **App Settings → PPM → Mapping → Start Calibration.** Sweep the tester through
   its full range, then apply. Without this the VESC doesn't know your pulse range.
5. **Control Type:** `Current No Reverse With Brake` is the usual choice for a
   scooter. Set positive/negative ramping times to taste.
6. **Leave Safe Start enabled**, and remember what it does: the motor will not
   start unless the throttle was at minimum when the VESC powered up. A tester
   parked mid-throttle at power-on looks exactly like a dead ESC.
7. **Write App Configuration** again.

### Verifying it worked

Close VESC Tool (it holds the serial port) and run:

```
python3 vesc_read.py
```

The `[ ppm / servo input ]` section should now show a last pulse around
**1000–2000 µs**. If it still reads 0 with the app enabled and the tester powered,
*then* it is genuinely a wiring problem — which is the thing we could not
distinguish before, because a disabled app reads 0 no matter how good the wiring is.

## FOC wizard — every screen, for this motor

Source: `mobile/SetupWizardFoc.qml`. Values below are read out of the preset tables,
not guessed.

### Screen 1 — USAGE  →  select **E-Skate**

| Preset | `l_duty_start` | `m_fault_stop_time_ms` | `bms.limit_mode` | cautious cutoff |
|---|---|---|---|---|
| Generic | 1.0 | 500 | 3 | yes |
| **E-Skate** | **0.85** | **50** | **3** | **yes** |
| Balance | 1.0 | 50 | 0 | no |
| Propeller | 1.0 | 500 | 3 | yes |

A kick scooter is an e-skate in all the ways that matter. The 50 ms fault-stop
recovers from a transient quickly instead of dropping out for half a second, and
`duty_start 0.85` leaves field-weakening headroom. **Leave Override unchecked.**

`batt_cut_cautious` is applied only after detection succeeds — E-Skate gives the
gentler low-voltage cutoff, which suits a 2.55 Ah pack.

### Screen 2 — MOTOR  →  **E-Bike DD hub motor**, with Override

It is the only hub-motor preset, and its openloop/sensorless ERPM values are the
ones that matter. Tick **Override (Advanced)** and change:

| Field | Preset | Set to | Why |
|---|---|---|---|
| Max Power Loss | 150 W | **50 W** | preset is for a 6 kg motor; yours is 150 W rated |
| Openloop ERPM | 300 | **300** | correct for a low-speed hub motor |
| Sensorless ERPM | 2000 | **2000** | correct |
| Motor Poles | 46 | **30** | our guess; no effect on detection |

**There is no "motor current max" field anywhere in this wizard.** The firmware
derives it from Max Power Loss. That single number *is* your motor current limit.

### Screen 3 — BATTERY

| Field | Value |
|---|---|
| Battery Type | **Li-ion 3.0/4.2 V** (`BATTERY_TYPE_LIION_3_0__4_2`) |
| Battery Cells Series | **6** |
| Battery Capacity | **2.55 Ah** |

Then **tick "Advanced (0 = defaults)"** — this matters, because 0 means *firmware
defaults on a 70 A ESC*:

| Field | Value |
|---|---|
| Battery Current Max | **8 A** |
| Battery Current Regen | **−3 A** (use **−1 A** on a bench supply) |

Both are passed directly into `detectAllFoc()`, so they take effect during detection.

### Screen 4 — SETUP

| Field | Value |
|---|---|
| Wheel Diameter | **measure your tire, in mm** — display only |
| **Direct Drive** | **CHECKED** — hub motor, no pulleys |
| Motor Poles | **30** |
| Motor Temperature Sensor Type | **Disabled** |
| NTC Motor Beta | ignore — unused when disabled |

### Then: the detection dialog

"WARNING: This is going to spin up all motors."

**"Detect all motors over CAN Bus" defaults to CHECKED — untick it.** One ESC, nothing
on the CAN bus. Wheel clamped; this spins harder than anything so far.

Detection should report **≈0.364 Ω** and **≈273 µH**. Close means healthy.

## Next steps, in order

Motor confirmed spinning under VESC Tool keyboard control (2026-10-06).

### 1. Back up the configuration — do this first
`Backup Configuration` in VESC Tool stores it against the ESC's UUID. You now have a
working config; protect it before touching anything else.

### 2. Verify the pole count
`pole_pairs = ERPM ÷ actual wheel RPM`. Run a steady speed, read ERPM, count real
wheel revolutions (phone slow-mo). Expect **15** (= 30 poles). Every speed and
odometer reading depends on this; nothing else does.

### 3. Pick the throttle input — this is the real decision

| Input | App setting | Use |
|---|---|---|
| Scooter's own thumb throttle | **ADC and UART** | the actual goal for a revive |
| CCPM servo tester | **PPM and UART** | bench stand-in only |

The servo tester was always a diagnostic prop. The E12's thumb throttle is a hall
unit with 3 wires (+5 V, signal, GND) and belongs on the **ADC** input, not PPM.
Pick `... and UART` either way so the ESP32 can talk to the VESC later without
redoing this.

**Measure the throttle's output range with a meter before connecting it.** A hall
throttle typically swings ~0.8–4.2 V on a 5 V supply; confirm what this ESC's ADC
input tolerates before wiring it in, and divide it down if needed. VESC Tool's ADC
app shows the live voltage, which is how you set the start/end points once it is
safely connected.

### 4. Three connectors to find in the scooter loom

| Connector | Wires | Goes to |
|---|---|---|
| Thumb throttle | 3 | ADC input |
| Brake lever | 2–3 | ADC2 or a digital input (the E12 has regen braking) |
| Motor hall sensors | 5 | sensor port, via a JST PH 2.0 6-pin adapter |

### 5. Halls — worthwhile, not blocking
See "Adding the hall sensors later". Sensorless is fine above ~0.8 km/h, and a kick
scooter is kick-started anyway. Halls buy standstill torque and clean hill starts.

## ⚠️ TEMPORARY bench settings — revert before riding

Set while running on a current-limited bench supply with no battery fitted
(2026-10-06). A supply cannot absorb regen current; a battery can.

| Parameter | Bench value | Restore to with battery |
|---|---|---|
| `l_in_current_min` — Battery Current Max Regen | **0 A** | **−3 A** |
| `l_current_min` — Motor Current Max Brake | **0 A** | **−10 A** |

Zeroing regen alone is not enough. Motor brake current is what *generates* the
energy; battery regen is only where it tries to go. Leave brake current non-zero
and the ESC still brakes, finds nowhere to put the energy, and pushes the bus
voltage up.

**With both at zero there is no electrical braking at all.** The wheel freewheels
and coasts a long time with no load — do not try to stop it by hand. And the E12's
stock braking includes regen, so riding in this state means the mechanical fender
brake is the only brake. Revert before it touches pavement.

Bench supply: **21–22 V, current limit 3–5 A.** Too tight a limit droops the voltage
into the 19.2 V cutoff mid-test and looks like a random power loss.

## Control type: Current works — the grinding was a tool conflict

**Corrected 2026-10-06.** An earlier version of this section claimed current control
could not start this motor from standstill and that Duty was required. That was wrong.

What actually happened: **VESC Tool's Keyboard Control was still active while the PPM
app was driving.** Both write motor setpoints continuously, at different rates, and
they fought — producing a grind with ~18 tachometer counts and no rotation. Disabling
Keyboard Control and rebooting fixed it with `Current No Reverse` unchanged.

**If the motor judders instead of spinning, check Keyboard Control first.** It is the
keyboard icon on the right-hand toolbar, and nothing warns you that it is contending
with the throttle.

| Control Type | Use |
|---|---|
| **`Current No Reverse` (2)** | **current choice** — works from standstill, good feel |
| `Current No Reverse With Brake` (3) | switch to this once a battery is fitted and brake/regen are restored |
| `Duty Cycle No Reverse` (5) | not needed; throttle maps to speed, bogs on hills |
| `PID Speed Control No Reverse` (7) | later upgrade — holds speed regardless of slope, needs tuning |

`ctrl_type` defaults to **0 = Off** — calibration alone will not make the motor move.

### Standstill vs loaded standstill

Starting unloaded on a clamped wheel is not the same as starting under a rider.
The stock E12 requires about **1.3 mph** before the motor engages — roughly
**820 ERPM** at 15 pole pairs, comfortably above VESC's 300 ERPM open-loop region.
The stock controller almost certainly detected this from back-EMF; no extra sensor
is needed, since every BLDC controller already measures it for commutation.

So expect a kick-start to be required on the road even though it spins up fine on
the bench. That is how the scooter was designed to be ridden.

## Working configuration (2026-10-08)

Scooter runs: throttle, proportional brake input, regen, LiPo. All values written and
read back directly from the ESC with `vesc_conf.py`, not typed into a UI.

### Measured motor model

| | Value | Source |
|---|---|---|
| Resistance | 0.1363 Ω | FOC detection (0.1419 Ω warm — 4%, thermal) |
| Inductance | 364.7 µH | detection |
| Flux linkage | 12.336 mWb | detection; **validated** — predicted 9,400 ERPM no-load at 21 V, measured 8,080 at 95% duty |
| Ld/Lq diff | 37.4 µH (~10%) | too low for HFI, see below |
| Poles | 30 (15 pole pairs) | confirmed by no-load speed; the preset's 46 was wrong |
| Torque constant | **0.278 N·m/A** | 1.5 × 15 × 0.012336 |

### Battery — 6S1P 2200 mAh 50C LiPo

```
l_battery_cut_start  20.4 V   (3.40 V/cell)
l_battery_cut_end    19.8 V   (3.30 V/cell)
si_battery_ah        2.2
si_battery_cells     6
```
Li-ion values (19.2/18.0) would over-discharge a LiPo — 18.0 V is 3.0 V/cell.

### Currents

```
l_current_max      40 A    burnout profile; 11.1 N·m, 109 N at the tyre
l_abs_current_max  60 A
l_in_current_max   20 A    at stall 40 A motor needs ~15 A battery, or it clamps
l_current_min     -20 A    motor brake
l_in_current_min   -6 A    regen ~2.7C into 2.2 Ah
```
**Stall dissipation is `1.5·I²·R`** — 40 A = 326 W into a 150 W motor with no airflow.
Burst only. Drop `l_current_max` to ~20 A for ordinary riding.

### Inputs

```
app_to_use                   5    ADC and UART
app_adc_conf.ctrl_type       8    Current No Reverse Brake ADC2
ADC1 throttle   0.90 → 2.59 V     rest 0.845 V
ADC2 brake      1.00 → 3.20 V     released ~0.37 V (floats), engaged 3.30 V
```
ADC2 start is 1.00 V not 0.50 V: the released input **floats** around 0.345–0.405 V,
and under ctrl_type 8 a float that drifts over the threshold becomes a brake command.
1.00 V gives 600 mV margin — the software substitute for a 10 kΩ pull-down.

### Sensorless starting

```
foc_sensor_mode            0     Sensorless
foc_openloop_rpm         300     DO NOT LOWER — see below
foc_sl_openloop_time_lock  0.2 s align rotor before rotating
foc_sl_openloop_boost_q    5.0 A fixed start current regardless of throttle
```

## Hard-won gotchas

**`foc_sl_openloop_boost_q` was 0.** Start current then follows the throttle, so a
light throttle can't drag the rotor out of its cogging detent. This is why starts were
intermittent. 5 A fixed it.

**`foc_openloop_rpm` must stay well above the observer's standstill noise.** That noise
reads **−13 to −87 ERPM** with the motor stopped. `foc_sl_openloop_hyst` means *"go to
openloop if ERPM has been below openloop RPM for this long"* — so lowering the threshold
to 150 let noise keep resetting the timer, open loop never engaged, no alignment, and
the motor needed a bump every time. 300 works. If intermittent starts return after a
long ride, re-measure that noise floor before changing anything else.

**HFI does not work on this motor.** Tried mode 3 and mode 5 (Silent). Both start at low
throttle then collapse completely at ~1/4 throttle — saturation shrinks an already
marginal 10% saliency. Surface-magnet hub motors lack the asymmetry HFI needs. This is a
property of the motor, not a tuning problem.

**Never re-run the full FOC detection wizard casually.** `measure_linkage` failed here
(motor never spun, just made noise) and returned **1.47×10¹³ Wb**. Detection would write
that, and observer gain is computed as `1000/λ²`, so a bogus λ destroys the observer.

**Config changes apply live — no reboot needed.** Demonstrated repeatedly: ctrl_type
changes took effect on the very next test. The classic "write then reboot" advice
conflates the reboot with finally clicking Write.

**VESC Tool holds the serial port exclusively.** Disconnect in the tool before using any
script here.

## Tooling

- [`vesc_read.py`](vesc_read.py) — identity, live values, PPM decode, faults
- [`vesc_adc.py`](vesc_adc.py) — live ADC1/ADC2 with min/max capture
- [`vesc_live.py`](vesc_live.py) — throttle level beside motor current/duty/ERPM, triggers on throttle
- [`vesc_conf.py`](vesc_conf.py) — **read/write any app or motor config parameter**
- [`vesc_spin.py`](vesc_spin.py) — open-loop spin test

`vesc_conf.py` derives byte offsets from the firmware's own `<SerOrder>` in
`parameters_*conf.xml`, reproduces VESC Tool's serializer (including `float32_auto`),
and refuses to run if the blob length doesn't match the computed layout. Writes are
read-modify-write, so fields it can't decode pass through byte-identical.

```
python3 vesc_conf.py motor get l_current_max
python3 vesc_conf.py motor set l_current_max 20
python3 vesc_conf.py app set app_adc_conf.ctrl_type 8
```

## Working configuration (verified on-ESC 2026-10-08)

Read back directly from the ESC with [`vesc_conf.py`](vesc_conf.py), not from the GUI.
Pack: 6S1P LiPo, 2200 mAh, 50C, 22.2 V nominal.

### Motor config

| Parameter | Value | Note |
|---|---|---|
| `l_current_max` | 40 A | burnout torque — 0.278 N·m/A → 11.1 N·m |
| `l_abs_current_max` | 60 A | hard trip |
| `l_in_current_max` | 20 A | must exceed ~15 A or 40 A gets clamped at stall |
| `l_current_min` | −20 A | motor brake |
| `l_in_current_min` | −6 A | regen ≈ 2.7C into 2.2 Ah |
| `l_battery_cut_start` / `_end` | 20.4 / 19.8 V | **LiPo** 3.40 / 3.30 V per cell |
| `si_battery_ah` / `_cells` | 2.2 / 6 | |
| `si_motor_poles` | 30 | confirmed by ERPM ÷ wheel RPM |
| `foc_sensor_mode` | Sensorless | motor has no halls |
| `foc_openloop_rpm` | 800 | ≈2 km/h — matches stock engagement point |
| `foc_sl_openloop_time_lock` | 0.2 s | **aligns rotor before spinning — fixes needing a kick** |
| `foc_sl_openloop_time_ramp` | 0.2 s | |
| `foc_sl_openloop_time` | 0.1 s | |

### App config

| Parameter | Value | Note |
|---|---|---|
| `app_to_use` | 5 (ADC and UART) | UART left on for the ESP32 later |
| `app_adc_conf.ctrl_type` | 8 (Current No Reverse Brake ADC2) | **8, not 7** — 7 reads RX/TX buttons, not ADC2 |
| ADC1 start / end | 0.90 / 2.59 V | throttle: rest 0.845, full 2.59 |
| ADC1 abs min / max | 0.50 / 2.90 V | broken-wire + short-to-rail guard |
| ADC2 start / end | 1.00 / 3.20 V | brake; 1.00 gives 600 mV over the 0.40 V float |
| `hyst` | 0.10 | input deadband |
| `multi_esc` | 0 | single ESC |

### Measured motor constants

```
R  = 0.1363 Ω      L = 364.74 µH      Lq-Ld = 37.40 µH (~10% saliency)
flux linkage = 12.34 mWb   →   0.278 N·m per amp
no-load ceiling ≈ (Vbus/√3)/λ : 20.6 km/h @ 21 V, ~27 km/h @ 25.2 V
```

### Still outstanding

- Brake is **proportional**, not a switch (holds ~1.59 V mid-travel) — ADC2 start of
  1.00 V costs the first ~20% of lever travel; lower toward 0.6–0.7 V for earlier bite
  at the cost of float margin.
- No motor temperature sensor. 40 A at stall is 326 W into a 150 W motor — burst only.
- `l_max_vin` is 57 V (hardware ceiling), so **regen has no overcharge protection** for a
  6S pack. Brake lightly on a freshly charged battery.

## ⚠️ OPEN ISSUE (2026-10-08) — inputs and terminal both dead

**Symptom:** both ADC channels report exactly `0.000 V`, and **all terminal commands
(`help`, `hw_status`, `volt`, `threads`) return no output at all.** Those same terminal
commands worked earlier the same session.

**Still working:** `COMM_GET_VALUES` (22.3 V, FET 30 °C, no faults), `COMM_GET_APPCONF`,
`COMM_GET_MCCONF`, config writes with correct readback, USB enumeration.

So core packet comms are fine while **two independent firmware subsystems are down**:
the ADC input app and the COMM_PRINT/terminal path. That pattern points at firmware
state — a hung or crashed thread — not at wiring.

### Eliminated (each tested, not assumed)

| Hypothesis | How it was ruled out |
|---|---|
| `app_to_use` wrong | read straight from the config blob: `5 (ADC and UART)` every time |
| Blown 3.3 V accessory rail | brake read a clean 3.296 V well after the first failure |
| `voltage_min` (Abs Min) guard | reverted it with no change, twice |
| Config-write stops the app | survived a full power cycle, which must restart it |
| Bad float32_auto encoder | 42/42 firmware-written fields round-trip **byte-exact** |
| Config drift | restored byte-identical to a known-good state; still zero |

### Try next, in order

1. **Re-check** — `python3 vesc_read.py --term "help"`. If terminal output is back, the
   state cleared on its own and that itself is a clue.
2. **Load Default Parameters** in VESC Tool, then reconfigure from the table above.
   Clears any config-induced bad state without touching flash.
3. **Re-flash firmware 6.06** from VESC Tool's firmware page. Wipes config — but the
   complete working configuration is recorded above, so it is cheap to restore.

Nothing is lost: every setting is written down, and `vesc_conf.py` can replay them.

### Known-good hardware baseline (all verified this session)

Motor spins to 8,083 ERPM (~20.6 km/h) on throttle · thumb throttle 0.845→2.59 V ·
brake lever proportional 0.35→3.30 V · R 0.1363 Ω · L 364.74 µH · λ 12.34 mWb ·
30 poles · no faults · FET temp never above 31 °C.

## If something doesn't work

`Terminal → faults` is the first stop — it logs why the ESC refused or shut down,
which is far more informative than watching a motor not move.
