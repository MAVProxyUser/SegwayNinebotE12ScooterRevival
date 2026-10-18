// E12 deck plate - hole pattern gauge
// The photo gives ~108 px/inch with only ~4% perspective variation, but the
// holes themselves are dark-on-black and could not be located reliably.
// So this does not assume a pitch - it measures one.
//
// USE: lay the gauge on the plate, slide until a labelled row drops onto two
// adjacent holes. That row's number is the pitch in mm.

$fn = 64;

T        = 3;        // plate thickness
HOLE_D   = 5.5;      // clearance holes - slip over a bolt/pin, see through
LABEL_H  = 0.8;      // embossed text height
LABEL_SZ = 7;

// ---- Part A: longitudinal pitch gauge -------------------------------------
PITCHES  = [110, 114, 118, 122, 126];   // mm, brackets the ~4.6" visual estimate
ROW_DY   = 18;
A_W      = 150;
A_H      = len(PITCHES) * ROW_DY + 8;

module partA() {
  difference() {
    cube([A_W, A_H, T]);
    for (i = [0 : len(PITCHES)-1]) {
      p  = PITCHES[i];
      cy = 8 + i*ROW_DY + ROW_DY/2;
      translate([A_W/2 - p/2, cy, -1]) cylinder(d=HOLE_D, h=T+2);
      translate([A_W/2 + p/2, cy, -1]) cylinder(d=HOLE_D, h=T+2);
    }
  }
  // embossed pitch labels, centred between each pair
  for (i = [0 : len(PITCHES)-1]) {
    cy = 8 + i*ROW_DY + ROW_DY/2;
    translate([A_W/2, cy, T])
      linear_extrude(LABEL_H)
        text(str(PITCHES[i]), size=LABEL_SZ, halign="center", valign="center");
  }
}

// ---- Part B: hole diameter gauge ------------------------------------------
DIAMS  = [3.5, 4, 4.5, 5, 5.5, 6];
B_DX   = 17;
B_W    = len(DIAMS) * B_DX + 8;
B_H    = 30;

module partB() {
  difference() {
    cube([B_W, B_H, T]);
    for (i = [0 : len(DIAMS)-1])
      translate([8 + i*B_DX, B_H - 10, -1]) cylinder(d=DIAMS[i], h=T+2);
  }
  for (i = [0 : len(DIAMS)-1])
    translate([8 + i*B_DX, 7, T])
      linear_extrude(LABEL_H)
        text(str(DIAMS[i]), size=5, halign="center", valign="center");
}

partA();
translate([0, A_H + 6, 0]) partB();
