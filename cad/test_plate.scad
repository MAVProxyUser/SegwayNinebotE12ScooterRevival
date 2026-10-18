// E12 deck plate - hole pattern TEST PLATE
// Measured by hand 2026-10-18: 3 hole pairs, 120 mm pitch, 90 mm across,
// plate ~96 x ~375 mm.
//
// NOTE ON WIDTH: 90 mm spacing on a 96 mm plate leaves only 3 mm from hole
// centre to edge - under 1 mm of material around a 4.5 mm hole. That breaks
// out in plastic, so PLATE_W defaults to 102 mm here. The HOLE PATTERN is
// exactly as measured; only the outline is widened so the test piece survives.
// Set PLATE_W = 96 to reproduce the stated outline.

$fn = 64;

PLATE_L   = 375;    // overall length
PLATE_W   = 102;    // see note above (stated: 96)
T         = 3;      // thickness
PITCH     = 120;    // longitudinal centre-to-centre
SPAN_W    = 90;     // cross-plate hole to hole
FIRST_X   = 15;     // first pair from the left end; photo suggests ~10-15
HOLE_D    = 5.0;    // clearance
N_PAIRS   = 3;

LABEL_H   = 0.8;

module holes() {
  for (i = [0 : N_PAIRS-1]) {
    x = FIRST_X + i*PITCH;
    translate([x, PLATE_W/2 - SPAN_W/2, -1]) cylinder(d=HOLE_D, h=T+2);
    translate([x, PLATE_W/2 + SPAN_W/2, -1]) cylinder(d=HOLE_D, h=T+2);
  }
}

module labels() {
  translate([FIRST_X + PITCH, PLATE_W/2, T])
    linear_extrude(LABEL_H)
      text("120 / 90", size=10, halign="center", valign="center");
}

module plate_full() {
  difference() { cube([PLATE_L, PLATE_W, T]); holes(); }
  labels();
}

// ---- split halves, for beds under 375 mm --------------------------------
// Lap joint at the midpoint with two alignment pin holes, so the two halves
// register to each other rather than relying on eyeballing.
CUT      = PLATE_L/2;
LAP      = 40;
PIN_D    = 4.2;

module half_A() {
  difference() {
    union() {
      cube([CUT, PLATE_W, T]);
      translate([CUT, PLATE_W/2 - 15, 0]) cube([LAP, 30, T/2]);   // tongue
    }
    holes();
    for (dx=[12, 28]) translate([CUT+dx, PLATE_W/2, -1]) cylinder(d=PIN_D, h=T+2);
  }
}

module half_B() {
  difference() {
    union() {
      translate([CUT, 0, 0]) cube([PLATE_L-CUT, PLATE_W, T]);
      translate([CUT-LAP, PLATE_W/2 - 15, T/2]) cube([LAP, 30, T/2]); // pocket mate
    }
    translate([CUT-LAP-0.2, PLATE_W/2 - 15.2, -0.1]) cube([LAP+0.4, 30.4, T/2+0.1]);
    holes();
    for (dx=[12, 28]) translate([CUT+dx, PLATE_W/2, -1]) cylinder(d=PIN_D, h=T+2);
  }
}

MODE = "full";   // "full" | "split"

if (MODE == "full") plate_full();
else { half_A(); translate([0, PLATE_W + 8, 0]) half_B(); }
