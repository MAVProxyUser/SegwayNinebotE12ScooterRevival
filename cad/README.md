# CAD — E12 deck plate

Parametric OpenSCAD sources plus exported STLs. Regenerate any STL with:

```bash
openscad -o cad/slide_baseA.stl -D 'PART="baseA"' cad/slide_door.scad
```

## Deck plate geometry (as measured 2026-10-18/19)

| | |
|---|---|
| Plate | **375 × 96 mm** (modelled 102 — see note) |
| Hole pairs | **4** |
| Longitudinal pitch | **120 mm** → holes at **7.5 / 127.5 / 247.5 / 367.5** |
| Cross-plate spacing | **90 mm** |

4 pairs at 120 mm span 360 mm, leaving 7.5 mm at each end. That matches the
reference photo, where hole-like features read at ~10, ~119, ~239 and ~371 mm.

**Width note:** 90 mm spacing on a 96 mm plate puts hole centres 3 mm from the
edge — under 1 mm of material around a 5 mm hole, which snaps in PLA. The models
use `PLATE_W = 102` so test parts survive. Hole positions are unchanged; set
`PLATE_W = 96` for the true outline.

---

## `slide_door.scad` — sliding battery access door

Three parts. Split at **x = 280** so the rails, the opening and three hole pairs
stay wholly in part A; nothing that must stay aligned crosses the joint.

| STL | Size | Contents |
|---|---|---|
| `slide_baseA.stl` | 280 × 102 × 8 | rails, opening, fasteners 1–3 |
| `slide_baseB.stl` | 135 × 102 × 3 | tongue, fastener 4 |
| `slide_door.stl` | 109 × 65 × 5.4 | sliding panel + finger tab |

### Slide mechanism

C-channel rails: a 4 mm wall standing 3 mm off the plate with a 3 mm lip
overhanging inward. The 2.4 mm door runs in the 3.0 mm channel with 0.4 mm side
clearance. Rails sit at y=18/84, **inboard of the fasteners at y=6/96**, so the
plate can still be bolted down with the door fitted. An end stop prevents the
door sliding out of the retracted end.

### The joint

35→**40 mm half-thickness lap**. Part B carries the tongue reaching *back* into
part A, so A's footprint is exactly the split length rather than split+lap.

Two integral **registration keys** (10 × 5 × 1.2 mm, 0.25 mm clearance) on the
tongue drop into pockets in A's rebate — the halves self-align and hold with glue
alone, no separate pins or hardware.

Better still, **the x=247.5 fastener passes through the lap**, so a real bolt
clamps both halves to the frame.

> The lap is 40 mm and not 35 for a specific reason: at 35 the tongue began at
> x=245 and the 5 mm hole at 247.5 spanned exactly 245.0–250.0, leaving the hole
> wall tangent to the tongue's back face. Zero-thickness contact — the mesh came
> out non-manifold. Rails were trimmed 3 mm to stay clear of the deeper tongue.

### Printing

All three parts print flat, no supports. Part B prints tongue-down with the
registration keys facing up — check your slicer doesn't auto-flip it.

---

## `test_plate.scad` — plain hole-pattern test

`test_plate.stl`, 375 × 102 × 3, hole pattern only, no mechanism. For checking
the pattern against the scooter before committing to the full assembly.

## `hole_gauge.scad` — measuring gauge

`hole_gauge.stl`, 150 × 134 × 3. Built when the hole pitch was still unknown:
five labelled hole pairs (110–126 mm) and a 3.5–6 mm diameter gauge. Superseded
by the measured 120 mm pitch, kept because it is a useful general tool.

---

## Open

- **Opening is 95 × 60 mm** in the middle bay. A 6S 2200 LiPo is typically
  ~135 mm long, so it likely will not lift out vertically. Moving the opening or
  spanning a bay boundary are one-line changes — needs the pack's L × W × H.
- **Hole diameter is assumed 5.0 mm.** Not measured.
