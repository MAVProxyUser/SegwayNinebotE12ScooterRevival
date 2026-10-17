# A Kids' Scooter, A VESC, And A Week Lost To Three Zeroes

When a Segway Ninebot Zing E12 entered service on [20 March 2026](https://x.com/d0tslash/status/2034853027245441426),
nobody expected to be shopping for a replacement by [5 April](https://x.com/d0tslash/status/2040804531177414815).
Two weeks. The motor and battery were fine — the controller simply stopped.

The obvious move is another scooter. [Kevin Finisterre](https://github.com/MAVProxyUser/SegwayNinebotE12ScooterRevival)
instead bolted a **Flipsky Mini FSESC6.7 Pro** to it: a 70 A VESC driving a 150 W hub
motor, which is roughly like fitting a dragster engine to a shopping trolley. The
interesting part is everything that had to be discovered along the way.

There is no datasheet for this motor, so it got characterised from scratch —
**0.1363 Ω, 352 µH, 12.34 mWb** of flux linkage. The pole count isn't printed anywhere
either, so it was derived by commanding a known ERPM and counting actual wheel
revolutions: 30 poles. That number got a second, satisfying confirmation from physics.
Flux linkage sets a no-load speed ceiling, and at 15 pole pairs it predicts 20.6 km/h —
which is what the wheel did. At 23 pole pairs it would predict 13.4 km/h, *below* the
scooter's own rated top speed, and therefore impossible.

It turns out the motor has no Hall sensors at all, so everything runs sensorless. That
sounds like a compromise until you remember the stock scooter only engages its motor
above about 1.3 mph. It was always a *kick* scooter; the factory controller just never
tried to start from a standstill either.

The stock thumb throttle and brake lever both survived the transplant onto the VESC's
ADC inputs — and the brake turned out to be a proportional hall lever rather than the
simple cutoff switch everyone assumes, so it drives genuine modulated regen braking.

Then the ESC died for a week.

Both ADC inputs read a hard zero. Every terminal command returned nothing. It survived
power cycles and seven days unplugged. The cause was three numbers: the FOC current
sense offsets, which should sit near 2048 — the ADC midpoint — had become `0.00 0.00
0.00`. With no offset, an ordinary idle reading is interpreted as about 165 A, so the
firmware saw a phantom **−72 A at zero duty, zero RPM** and tripped its absolute
overcurrent protection at every boot.

The elegant part is why it wouldn't clear. VESC recalibrates those offsets on boot — but,
per its own documentation, *"calibration on boot will fail if there is a fault code active
during boot."* The bad offsets caused the fault; the fault blocked the fix. And a second
flag, *Write Enabled*, was off, meaning known-good offsets restored from a config backup
were **silently discarded**. Only a full motor detection broke the loop.

Getting there meant writing Python that speaks the VESC packet protocol directly,
deriving the exact config serialiser from VESC Tool's own parameter XML rather than
guessing byte offsets — so any parameter can be read or written without the GUI.

The [repository](https://github.com/MAVProxyUser/SegwayNinebotE12ScooterRevival) has the
tooling, the full working configuration, and — refreshingly — every wrong hypothesis
that got disproved on the way. Including the first controller tried: an MKS Dual FOC,
a gimbal driver specified for windings above 10 Ω, attached to a 0.1363 Ω motor. Off by
a factor of seventy.
