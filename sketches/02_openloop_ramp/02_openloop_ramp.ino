/*
 * 02_openloop_ramp  --  first powered spin of the E12 hub motor
 *
 * This is the "low throttle, ramp up" test. OPEN LOOP: the Hall sensors are
 * not used at all, so a wrong pole count or a miswired hall connector cannot
 * run the motor away. The ESP32 just generates a rotating field and the rotor
 * follows it -- or doesn't, which is itself useful information.
 *
 * *** READ sketches/README.md BEFORE APPLYING POWER ***
 * Short version: wheel off the ground and clamped, bench supply at 12V with
 * the current limit set to ~1.5A, voltage_limit starts at 0.5V.
 *
 * In open loop the phase current is set by VOLTAGE_LIMIT / phase_resistance,
 * NOT by the speed. A hub motor phase is ~0.2-0.5 ohm, so 1.0V is already
 * 2-5A. Raise VOLTAGE_LIMIT in 0.25V steps and watch the supply's ammeter.
 *
 * Serial commands (115200 baud, newline ending):
 *   g        start the ramp profile
 *   x        STOP now + disable driver
 *   v<num>   set voltage limit, e.g.  v0.75
 *   t<num>   set peak target velocity in rad/s, e.g.  t12
 *   r<num>   set ramp time in seconds, e.g.  r8
 *   d        reverse direction
 *   i        print settings
 */

#include <SimpleFOC.h>

// ---------------------------------------------------------------------------
// PINS -- from the official MKS DUAL FOC V3.1 schematic (makerbase-mks/MKS-DUALFOC).
// The board has a 2x13 socket for an ESP32 devkit module; these GPIO numbers are
// hard-wired to the driver by the PCB, and the socket is silkscreened with them.
// Your Thing Plus is a Feather footprint and will NOT plug in -- run jumpers to
// the socket pins by their printed numbers. Keeping the same numbers on the
// Thing Plus side means all of Makerbase's stock examples work unmodified.
//
//   M0: IN1=32 IN2=33 IN3=25 EN=22     M1: IN1=26 IN2=27 IN3=14 EN=12
//   M0 current sense: phaseA=39 phaseB=36   M1: phaseA=35 phaseB=34
//   Encoder/I2C port 0: SCL_0=18 SDA_0=19 I_0=15
//   Encoder/I2C port 1: SCL_1=5  SDA_1=23 I_1=13
//   UART on H1: TXD=17 RXD=16
//
// NOTE: GPIO12 (M1_EN) is the ESP32 MTDI strapping pin. Only relevant if you
// wire up motor 1 -- the E12 has one hub motor, so leave M1 unconnected.
// ---------------------------------------------------------------------------
#define M0_IN1 32
#define M0_IN2 33
#define M0_IN3 25
#define M0_EN  22

// ---------------------------------------------------------------------------
// MOTOR / SUPPLY
// ---------------------------------------------------------------------------
#define POLE_PAIRS        15     // <-- from sketch 01. Open loop still spins if
                                 //     this is wrong, just at a different speed.
#define SUPPLY_VOLTS      12.0f  // actual bench supply voltage.
                                 // *** The V3.2 Plus is listed at 12-24V input. Check
                                 // *** your pack voltage against that BEFORE going to pack.
#define VOLTAGE_LIMIT_0    0.5f  // START HERE. Raise with 'v' one notch at a time.
#define TARGET_VEL_0       6.0f  // rad/s mechanical at the top of the ramp
#define RAMP_SECONDS_0     6.0f
#define HOLD_SECONDS       3.0f
#define MAX_RUN_SECONDS   30.0f  // dead-man timer

BLDCMotor       motor  = BLDCMotor(POLE_PAIRS);
BLDCDriver3PWM  driver = BLDCDriver3PWM(M0_IN1, M0_IN2, M0_IN3, M0_EN);

enum Phase { IDLE, RAMP_UP, HOLD, RAMP_DOWN };
Phase  phase        = IDLE;
float  voltageLimit = VOLTAGE_LIMIT_0;
float  targetPeak   = TARGET_VEL_0;
float  rampSeconds  = RAMP_SECONDS_0;
float  dirSign      = 1.0f;
float  target       = 0.0f;
unsigned long phaseStart = 0;
unsigned long runStart   = 0;
unsigned long lastPrint  = 0;

void allStop(const char *why) {
  target = 0;
  motor.move(0);
  driver.disable();
  phase = IDLE;
  Serial.printf("\n>> STOP (%s). Driver disabled. Send 'g' to run again.\n", why);
}

void printInfo() {
  Serial.printf("\n-- voltage_limit %.2f V | target_peak %.2f rad/s | ramp %.1f s | dir %+.0f | supply %.1f V | pole_pairs %d\n",
                voltageLimit, targetPeak, rampSeconds, dirSign, SUPPLY_VOLTS, POLE_PAIRS);
  Serial.printf("-- approx wheel speed at peak: %.1f km/h (8in wheel)\n\n",
                targetPeak * 0.1016f * 3.6f);
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println(F("\n=== E12 open-loop ramp ==="));

  driver.voltage_power_supply = SUPPLY_VOLTS;
  driver.voltage_limit        = SUPPLY_VOLTS / 2.0f;
  if (!driver.init()) {
    Serial.println(F("driver.init() FAILED -- check pins/PWM channels"));
    while (1) delay(1000);
  }
  motor.linkDriver(&driver);

  motor.controller   = MotionControlType::velocity_openloop;
  motor.voltage_limit = voltageLimit;
  motor.velocity_limit = 100;

  // Optional and better: measure phase-to-phase R with a meter, halve it for
  // the per-phase value, then let SimpleFOC current-limit for you:
  //   motor.phase_resistance = 0.25f;
  //   motor.current_limit    = 1.0f;
  //
  // NOTE: do not count on this board's inline current sensing to protect you.
  // The INA181A2 amps have REF tied to GND on the V3.1 schematic, making them
  // unidirectional -- SimpleFOC's InlineCurrentSense needs a mid-rail bias.
  // voltage_limit IS your current limiter here. Keep it low.

  motor.init();
  driver.disable();

  printInfo();
  Serial.println(F("Driver is DISABLED. Set 'v' low, then send 'g' to start the ramp."));
}

void handleSerial() {
  static char buf[24];
  static uint8_t n = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      buf[n] = 0;
      if (n) {
        float val = atof(buf + 1);
        switch (buf[0]) {
          case 'g': case 'G':
            phase = RAMP_UP;
            phaseStart = runStart = millis();
            motor.voltage_limit = voltageLimit;
            driver.enable();
            Serial.println(F(">> RAMP UP"));
            break;
          case 'x': case 'X': allStop("user"); break;
          case 'v': case 'V':
            voltageLimit = constrain(val, 0.0f, SUPPLY_VOLTS / 2.0f);
            motor.voltage_limit = voltageLimit;
            Serial.printf(">> voltage_limit = %.2f V\n", voltageLimit); break;
          case 't': case 'T': targetPeak  = val; Serial.printf(">> target_peak = %.2f rad/s\n", targetPeak); break;
          case 'r': case 'R': rampSeconds = max(0.5f, val); Serial.printf(">> ramp = %.1f s\n", rampSeconds); break;
          case 'd': case 'D': dirSign = -dirSign; Serial.printf(">> dir %+.0f\n", dirSign); break;
          case 'i': case 'I': printInfo(); break;
          default: Serial.println(F("?? g x v<n> t<n> r<n> d i")); break;
        }
      }
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
}

void loop() {
  handleSerial();

  float t = (millis() - phaseStart) / 1000.0f;

  switch (phase) {
    case IDLE:
      target = 0;
      break;
    case RAMP_UP:
      target = targetPeak * (t / rampSeconds);
      if (t >= rampSeconds) { target = targetPeak; phase = HOLD; phaseStart = millis();
                              Serial.println(F(">> HOLD")); }
      break;
    case HOLD:
      target = targetPeak;
      if (t >= HOLD_SECONDS) { phase = RAMP_DOWN; phaseStart = millis();
                               Serial.println(F(">> RAMP DOWN")); }
      break;
    case RAMP_DOWN:
      target = targetPeak * (1.0f - t / rampSeconds);
      if (t >= rampSeconds) { allStop("profile complete"); }
      break;
  }

  if (phase != IDLE && (millis() - runStart) > (unsigned long)(MAX_RUN_SECONDS * 1000)) {
    allStop("dead-man timer");
  }

  motor.move(dirSign * target);

  if (millis() - lastPrint > 200) {
    lastPrint = millis();
    if (phase != IDLE) {
      Serial.printf("t=%5.1fs  target=%6.2f rad/s  (%5.2f km/h)  Vlim=%.2f\n",
                    t, dirSign * target, fabs(target) * 0.1016f * 3.6f, motor.voltage_limit);
    }
  }
}
