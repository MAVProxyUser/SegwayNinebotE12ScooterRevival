# E12 hub motor bench test

> **Update:** a Flipsky Mini FSESC6.7 Pro is now the intended driver — see
> [../VESC_SETUP.md](../VESC_SETUP.md). The MKS analysis below is kept for reference.
> **Sketch 01 is still worth running**: it verifies the Hall sensors and gives you the
> pole-pair count, which VESC needs as *poles* (= 2 × pole pairs) during motor detection.

> ## Can the MKS Dual FOC drive this motor? Marginal — one measurement decides it.
>
> **E12 actual specs:** 150 W motor, 21.6 V nominal pack (25.2 V max charge),
> 55 Wh, 18 km/h. Confirm against the label on your own pack.
>
> **MKS Dual FOC V3.2 Plus:** 12–24 V, listed 12 A peak. (V3.1, which the only
> published manual covers: 120 W/channel, ~5 A.)
>
> 150 W at 21.6 V is about **7 A**. That is inside 12 A peak. So this is not a
> wildly wrong board — it is a *marginal* one. Four real problems, in order:
>
> 1. **25.2 V fully charged vs a 24 V rating.** 5 % over. Bench-test well below
>    it; on the pack, either accept the risk or don't charge to full.
> 2. **Phase resistance.** The board is specified for gimbal motors with
>    **> 10 Ω** windings, because SimpleFOC's default voltage mode uses the
>    winding itself as the current limiter. Your motor is far below that.
>    Normally the fix is FOC *current* mode — but see 3.
> 3. **The onboard current sensing is wired unidirectional.** The INA181A2's
>    REF pin is tied to GND (V3.1 schematic, U6–U9), so it reads one polarity
>    only. SimpleFOC's `InlineCurrentSense` needs bidirectional sensing with a
>    mid-rail offset. So the current-mode escape hatch is closed, and you are
>    stuck in voltage mode with the winding as your only limiter.
> 4. **Thermals.** 150 W through a board Makerbase says needs a 25×25 mm
>    heatsink at *gimbal* power levels.
>
> Plus: no Hall support in any official routine (encoders are I²C/ABI/analog/
> PWM). SimpleFOC's `HallSensor` on the encoder-port GPIOs works anyway — see §4.
>
> ### The measurement that decides it
>
> **Phase-to-phase resistance of your motor** (§1). In voltage mode, stall
> current ≈ `voltage_limit ÷ phase_resistance`:
>
> | Phase-to-phase | Per phase | 3 V limit → stall | Verdict |
> |---|---|---|---|
> | 2.0 Ω | 1.0 Ω | 3 A | workable |
> | 1.0 Ω | 0.5 Ω | 6 A | tight but testable |
> | 0.4 Ω | 0.2 Ω | 15 A | over 12 A peak — don't |
>
> A 150 W hub motor is often around 1 Ω phase-to-phase, which is why this is
> worth testing rather than writing off. Measure first, then decide.
>
> **Everything below assumes the wheel is off the ground and you start at
> `voltage_limit = 0.5 V`.** If the board can't do it, §7 has alternatives.
>
> *Caveat: all board analysis here comes from the V3.1 / DengFOC files, the only
> ones published. Your V3.2 Plus has a different power stage and may differ in
> ways I cannot verify. Photograph your board's silkscreen and check.*

Three staged sketches. Do not skip ahead; each one de-risks the next.

| Sketch | Motor powered? | Proves |
|---|---|---|
| `01_hall_check` | **no** | Hall sensors alive, state sequence legal, **pole pairs** |
| `02_openloop_ramp` | yes, low volts | Driver turns all 3 phases, motor turns, no shorts |
| `03_hall_closedloop` | yes | Halls + FOC agree, throttle → speed |

---

## 0. Before anything: bench setup

- Wheel **off the ground and clamped**. A free-spinning hub motor that grabs is genuinely dangerous — it will throw the fork around. Clamp the fork/axle in a vise or bolt it to a board.
- Eye protection. Nothing loose near the tire.
- **Check the pack voltage against the board's input rating first.** The V3.2 Plus is listed at **12–24 V**. Measure your E12 pack at full charge — if it exceeds 24 V, the pack never goes on this board without you first confirming the real rating from Makerbase.
- **Power from a current-limited bench supply, not the pack.** Start at **12 V, 1.5 A limit**. The supply's limiter is your fuse and your instrumentation. If you have no bench supply, put an automotive blade fuse (3–5 A) in the pack positive and keep a hand on the disconnect.
- Original Ninebot controller **fully disconnected** from the motor.
- Common ground between the ESP32 and the MKS board. Everything downstream fails weirdly without it.
- Power the MKS board from the bench supply, power the ESP32 from USB. Do not try to backfeed the ESP32 from the motor rail on the first run.

## 1. Check the motor itself before you drive it

Two multimeter checks that catch a dead motor in 60 seconds:

1. **Phase resistance.** Measure between each pair of the three fat phase wires. All three readings should match within ~10 % and be a fraction of an ohm (hub motors are typically 0.2–0.6 Ω phase-to-phase; your meter's lead resistance is a big chunk of that, so null it out first). One reading much higher = open winding. Any phase to the axle/frame should be open (megohms) — continuity there means a burnt-through winding.
2. **Back-EMF.** Meter on AC volts across two phases, spin the wheel briskly by hand. You should see a few volts AC. Repeat on the other two pairs; they should match. Scope it if you have one — you want three clean, evenly-spaced trapezoid/sine waves.

If both pass, the motor is fine and the fault was in the old controller or battery.

## 2. Identify the Hall wires on the motor

Usually 5 wires. **Find +5 V and GND with a meter before applying anything** — most are red = +5 V, black = GND, and three signal wires, but don't trust colors on a Ninebot.

Per Hall signal wire: 4.7 kΩ pull-up to the ESP32's **3V3** rail. Power the Halls from **5 V** (VUSB on the Thing Plus), not 3V3 — SS41-class hall ICs get flaky below ~4 V. Hub-motor halls are nearly always open-collector, so pulling up to 3.3 V gives you 3.3 V logic from a 5 V-powered sensor.

**Verify this before connecting to the ESP32:** with only 5 V + GND + one pull-up to 3V3 connected, the output must swing 0 V ↔ ~3.3 V as you turn the wheel. If it swings 0 ↔ 5 V it's push-pull and needs a divider or level shifter.

## 3. Board pinout — what is actually verified, and what is not

Source files: `makerbase-mks/MKS-DUALFOC` → `Hardware/Schematic_MKS DUAL FOC V3.1.pdf` and `PCB_MKS DUAL FOC V3.1.pdf`. **Read the caveat at the end of this section before trusting any of it for a V3.2 Plus.**

### Connectors on the V3.1 board — confirmed from the PCB artwork

That is the complete list. Four mounting holes, and nothing else.

| Ref | Type | Function |
|---|---|---|
| **P3** | 2-pin 5 mm screw terminal | VIN / PGND — supply input |
| **P1** | 3-pin 5 mm screw terminal | motor 0 phases (`M0_OUT1_N`, `M0_OUT2_N`, `M0_OUT3`) — the **A0/B0/C0** terminal |
| **P2** | 3-pin 5 mm screw terminal | motor 1 phases — the **A1/B1/C1** terminal |
| **H1** | 2×9 (18-pin) 0.1" header | the only logic connector |

Phase order on P1 does **not** matter. Any of the six permutations will run; swapping any two reverses direction. Opposite of the Hall connector, where order matters a great deal.

### H1 carries

UART (TXD, RXD) · I²C bus 0 (SDA_0, SCL_0) · I²C bus 1 (SDA_1, SCL_1) · two spare logic lines (I_0, I_1) · VCC-3.3V · VCC-5V · several GND. Two pins are unconnected.

Two useful details confirmed from the schematic:

- **RN1** (4.7 kΩ ×4) pulls SDA_0, SCL_0, SDA_1, SCL_1 up to 3.3 V. **RN2** pulls I_0 and I_1 up to 3.3 V, and pulls **M0_EN / M1_EN down to GND** — so the drivers are disabled until the MCU actively drives enable high. Good default.
- That gives you **six logic lines already pulled up 4.7 kΩ to 3.3 V, with 5 V and GND on the same connector.** Which is exactly what a set of open-collector hub-motor Hall sensors wants (see §4).

### GPIO assignments — reference-design intent, NOT verified on your board

The schematic routes its nets to a symbol `U2` carrying these GPIO names:

```
M0: IN1=32 IN2=33 IN3=25 EN=22      M1: IN1=26 IN2=27 IN3=14 EN=12
M0 current sense: phaseA=39(VN) phaseB=36(VP)    M1: phaseA=35 phaseB=34
SDA_0=19 SCL_0=18   SDA_1=23 SCL_1=5   I_0=15 I_1=13   TXD=17 RXD=16
```

These match what the SimpleFOC community uses for MKS ESP32 FOC boards, so they are probably right. But treat them as intent, not fact — see below.

### Why you should verify against your own board

1. **`U2` has no footprint on the PCB.** It is a 26-pin schematic symbol with no corresponding land pattern anywhere in the layout. There is no ESP32 socket on this board.
2. **The PWM, enable, and current-sense nets have nowhere physical to go.** They terminate at `U2`, and H1 does not carry them.
3. **The title block reads "Deng FOC V3.0 / Company: Toan / 2021-01-29."** These are the open-source DengFOC design files, not an MKS-drawn document for the product in the repo's name.
4. **There is no published schematic for the V3.2 Plus at all,** and its power stage is different from V3.1 (V3.1 = L6234 driver ICs; the Plus reportedly uses an EG-series gate driver with discrete FETs, listed 12–24 V / 12 A peak).

So: read your own silkscreen, and ring out the terminals with a meter before wiring anything.

### Current sensing — present, but not usable for FOC as wired

Four INA181A2 amps (gain 50 V/V) on 0.01 Ω shunts, inline on phases A and B of each channel. Tempting, but on the V3.1 schematic **the REF pin is tied to GND** (U6–U9), which makes them unidirectional: 0 to about 6.4 A in one direction, and the other half of the phase waveform clips at zero.

SimpleFOC's `InlineCurrentSense` needs bidirectional sensing biased to mid-rail. So don't plan on FOC current control to protect the board — you're in voltage mode, and `voltage_limit` is your only current limiter. That's what makes §1's resistance measurement the deciding number.

They are still fine as a rough one-directional current readout if you want telemetry.

## 4. Halls — there is no Hall connector

The V3.1 board has no header labeled for Hall sensors. It is designed around **AS5600 magnetic encoders** on the two I²C buses, which is the normal SimpleFOC setup and not what a hub motor gives you.

That doesn't mean you're stuck. **Makerbase's own Hall example repurposes three of the logic lines on H1:**

```
Hall A -> 18 (SCL_0)   Hall B -> 19 (SDA_0)   Hall C -> 15 (I_0)
```

(`makerbase-motor/MKS-ESP32FOC`, `8_hallsensor_test.ino`)

Those three already carry 4.7 kΩ pull-ups to 3.3 V from RN1/RN2, which is exactly right for open-collector hub-motor Halls — **you do not need to add the external resistors.** Take the Hall's 5 V supply from `VCC-5V` on H1 and GND from one of H1's grounds, so the whole Hall connector lands on that one header.

Identify the H1 pin positions from your board's silkscreen, not from a pin table here.

## 5. Run order

```
01 → note pole pairs (transitions ÷ 6, commonly 15 for an 8" hub)
02 → v0.5, g   … watch the ammeter, raise voltage 0.25 V at a time
03 → arm, throttle up slowly
```

### What "good" looks like in sketch 02

- Supply current steady and roughly constant as speed ramps (open-loop current is set by `voltage_limit ÷ phase resistance`, not by speed).
- Motor turns smoothly, one direction, no audible grinding or squealing.
- If the motor **buzzes or twitches but doesn't turn**: `voltage_limit` too low for the friction, or one phase not connected.
- If it **turns then stutters as speed rises**: normal open-loop pull-out. Either raise `voltage_limit` slightly or lower the target. Not a fault.
- If current **spikes on enable**: kill power. Bad phase wiring or a driver fault.

### Tuning sketch 03

Start `PID_velocity.P = 0.05`, `I = 1.0`. Raise P until it responds crisply, back off 30 % when it starts to oscillate, then raise I to kill the steady-state droop. Raise `motor.voltage_limit` only after it tracks well at low speed.

## 6. Only then

Move up to the real pack voltage — **only if it is inside the board's input rating** — in one step, with the fuse still in and the wheel still off the ground. Re-check current draw at every stage. Wheel goes back on the ground last.

## 7. If the MKS board can't do it

If the resistance measurement rules it out, or it overheats under load, these all handle a 150 W / 21.6 V sensored hub motor without drama. Cheapest first:

1. **A generic 24 V/36 V hub-motor controller with Hall input** (~$15–30). Brushless scooter/e-bike controllers take three phase wires, five Hall wires, and a 0–5 V throttle. No code. Fastest path to a rolling scooter, no control over anything.
2. **A VESC** — Flipsky/Makerbase FSESC 4.20, or similar. 12–60 V, 50 A, native Hall sensor support, real FOC, and a UART/CAN API. This is the right pick if you want the ESP32 Thing Plus to stay in the project: it talks to the VESC over UART and you keep telemetry, current limiting and custom throttle logic without writing a commutation loop. Note Makerbase also sells VESC-family boards, so a "MKS" VESC is not the same product line as this Dual FOC.
3. **Repair the original Ninebot controller.** Worth a look first — if the fault is the battery or a blown FET, this is the cheapest fix and keeps the stock throttle and brake working.

Either way the MKS board isn't wasted — it's a capable SimpleFOC platform for a gimbal or small direct-drive project where the winding is 10 Ω or higher.

### What carries over

- Sketch 01 works unchanged — it is just the ESP32 reading three Hall lines.
- The pole-pair count you get from it is needed by every option above.
- The motor health checks in §1 apply no matter what drives it.
- Sketches 02/03 are stock SimpleFOC and will work against any SimpleFOC-supported driver rated for this motor; only the pin defines change.
