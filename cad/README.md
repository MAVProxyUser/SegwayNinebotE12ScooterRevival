# Hole pattern gauge

`hole_gauge.scad` / `hole_gauge.stl` — 150 × 134 × 3 mm, prints flat, no supports.

## Why a gauge and not a template

The reference photo (`IMG_4198.HEIC`) gives a usable scale — the ruler's ⅛″ ticks
resolve at ~108 px/inch and perspective varies only ~4% across the frame — but the
**holes themselves could not be located reliably**. They are dark features on a black,
dusty plate; automated detection returned more false minima from surface texture than
real holes, and the ruler sits in a different plane from the plate, adding parallax.

Best visual estimate was ~4 pairs at roughly 4.6″ (≈117 mm) pitch, with an honest
uncertainty around ±0.2″ (±5 mm). That is too loose to drill to, so this part measures
the pitch instead of assuming it.

## Part A — pitch gauge

Five labelled rows of hole pairs: **110, 114, 118, 122, 126 mm**, bracketing the
estimate in 4 mm steps. Lay the gauge on the plate and slide it until one row drops
onto two adjacent holes. That row's number is the pitch.

## Part B — diameter gauge

Six holes: **3.5, 4, 4.5, 5, 5.5, 6 mm**. Find the smallest that passes a fastener,
or offer each to a plate hole to read its size.

## Then what

With pitch and diameter known, the full pattern can be generated properly. The plate
is approximately **14.8″ (376 mm)** long overall, with holes inset from both long
edges and a stepped/castellated profile at one end.

Holes are 5.5 mm clearance so they slip over a bolt and you can sight through them.
