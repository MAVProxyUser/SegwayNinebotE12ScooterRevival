// E12 deck plate - sliding battery access door
//
// Part 1 (base): full plate, 6 mounting holes, rectangular access opening,
//                captive C-channel rails either side of the opening.
// Part 2 (door): panel that slides in those rails to expose/cover the opening.
//
// Rails sit INBOARD of the mounting holes (holes at y=6/96, rails at y=18/84)
// so they never clash. The opening sits BETWEEN hole pairs so no fastener is lost.
//
// Opening defaults to the widest clear bay. Set OPEN_X0/OPEN_X1 to move it.

$fn = 48;

PLATE_L = 375;
PLATE_W = 102;
T       = 3;

PITCH   = 120;
SPAN_W  = 90;
FIRST_X = 15;
HOLE_D  = 5.0;
N_PAIRS = 3;

// --- access opening (between hole pairs 2 and 3: x=135 and x=255) ---
OPEN_X0 = 150;
OPEN_X1 = 240;          // 90 mm clear
OPEN_W  = 60;           // across the plate

// --- slide hardware ---
DOOR_T    = 2.4;        // door thickness
CHAN_H    = 3.0;        // channel height (0.6 clearance over the door)
LIP       = 3;          // how far the lip overhangs inward
RAIL_W    = 4;          // rail wall thickness
CLR       = 0.4;        // side clearance

DOOR_L    = (OPEN_X1 - OPEN_X0) + 14;      // overlap each end
DOOR_W    = OPEN_W + 2*LIP;                 // sits under the lips
TRAVEL    = DOOR_L + 6;                     // retract room

RAIL_Y0 = PLATE_W/2 - DOOR_W/2;             // channel inner faces
RAIL_Y1 = PLATE_W/2 + DOOR_W/2;
RAIL_X0 = OPEN_X0 - TRAVEL;
RAIL_X1 = OPEN_X1 + 6;

module mount_holes() {
  for (i = [0 : N_PAIRS-1]) {
    x = FIRST_X + i*PITCH;
    translate([x, PLATE_W/2 - SPAN_W/2, -1]) cylinder(d=HOLE_D, h=T+2);
    translate([x, PLATE_W/2 + SPAN_W/2, -1]) cylinder(d=HOLE_D, h=T+2);
  }
}

module rail(ymin) {
  // vertical wall plus an inward lip at the top -> C-channel
  translate([RAIL_X0, ymin - RAIL_W, T]) cube([RAIL_X1-RAIL_X0, RAIL_W, CHAN_H + 2]);
  translate([RAIL_X0, ymin, T + CHAN_H])  cube([RAIL_X1-RAIL_X0, LIP, 2]);
}

module base() {
  difference() {
    cube([PLATE_L, PLATE_W, T]);
    translate([OPEN_X0, PLATE_W/2 - OPEN_W/2, -1])
      cube([OPEN_X1-OPEN_X0, OPEN_W, T+2]);
    mount_holes();
  }
  rail(RAIL_Y0);
  mirror([0,1,0]) translate([0,-PLATE_W,0]) rail(RAIL_Y0);
  // end stop so the door cannot slide out of the retracted end
  translate([RAIL_X0, RAIL_Y0 - RAIL_W, T]) cube([3, DOOR_W + 2*RAIL_W, CHAN_H + 2]);
}

module door() {
  difference() {
    union() {
      cube([DOOR_L, DOOR_W - 2*CLR, DOOR_T]);
      // finger tab
      translate([DOOR_L - 12, (DOOR_W - 2*CLR)/2 - 9, DOOR_T])
        cube([10, 18, 3]);
    }
    // grip ribs on the tab
    for (i=[0:3])
      translate([DOOR_L - 11 + i*2.4, -1, DOOR_T + 2.2])
        rotate([0,45,0]) cube([1.2, DOOR_W, 1.2]);
  }
}

PART = "base";    // "base" | "door"
if (PART == "base") base(); else door();
