/*
 * 03_hall_closedloop  --  Hall-sensored closed-loop velocity + throttle pot
 *
 * Only run this AFTER 01 (halls verified, pole pairs known) and 02 (motor
 * spins smoothly open loop at low voltage).
 *
 * Hall sensors give 6 counts per electrical revolution -- coarse. Expect
 * cogging/jitter below a few rad/s. That is normal and is not a wiring fault.
 *
 * Throttle is a 10k pot on THROTTLE_PIN (wiper to the pin, ends to 3V3/GND).
 * The scooter's own thumb throttle is a hall unit that wants 5V and outputs
 * roughly 0.8-4.2V -- do NOT feed that straight into the ESP32; divide it to
 * 0-3.3V first. Start with the bench pot.
 *
 * Safety features here: throttle must read zero at startup before the driver
 * is enabled, the commanded speed is slew-rate limited, and 'x' kills output.
 */

#include <SimpleFOC.h>

// --- pins: MKS DUAL FOC socket assignments, see sketch 02 header ------------
#define M0_IN1 32
#define M0_IN2 33
#define M0_IN3 25
#define M0_EN  22

// This board has NO Hall connector -- it is built for AS5600 magnetic
// encoders on two I2C buses. So the halls land on three of the logic lines
// on H1 (the 2x9 header, the board's only logic connector), which is what
// Makerbase's own hall example does. Those three already carry 4.7k
// pull-ups to 3V3 from RN1/RN2 -- no external resistors needed. H1 also
// has VCC-5V and GND, so the whole hall connector lands on one header.
// Find the H1 pin positions on your board's silkscreen.
#define H_A 18                   // SCL_0
#define H_B 19                   // SDA_0
#define H_C 15                   // I_0

// Leave motor 1 entirely unwired (the E12 has one hub motor), which frees
// GPIO34/35 -- otherwise driven by M1's current-sense amps -- for the pot.
#define THROTTLE_PIN 34          // ADC1, input-only pin -- fine for a pot

// --- motor / supply --------------------------------------------------------
#define POLE_PAIRS      15
#define SUPPLY_VOLTS    12.0f
#define VOLTAGE_LIMIT    2.0f    // start low, raise once it tracks well
#define MAX_VEL         20.0f    // rad/s at full throttle (~7 km/h on 8in)
#define SLEW_RAD_S2      6.0f    // how fast the command may change, rad/s^2

#define THR_RAW_MIN    120       // deadband floor (counts, 0-4095)
#define THR_RAW_MAX   4000

BLDCMotor      motor  = BLDCMotor(POLE_PAIRS);
BLDCDriver3PWM driver = BLDCDriver3PWM(M0_IN1, M0_IN2, M0_IN3, M0_EN);
HallSensor     sensor = HallSensor(H_A, H_B, H_C, POLE_PAIRS);

void doA() { sensor.handleA(); }
void doB() { sensor.handleB(); }
void doC() { sensor.handleC(); }

bool  armed     = false;
float command   = 0.0f;          // slew-limited target, rad/s
unsigned long lastLoop  = 0;
unsigned long lastPrint = 0;

float readThrottle() {           // -> 0.0 .. 1.0
  int raw = analogRead(THROTTLE_PIN);
  if (raw <= THR_RAW_MIN) return 0.0f;
  float f = (float)(raw - THR_RAW_MIN) / (float)(THR_RAW_MAX - THR_RAW_MIN);
  return constrain(f, 0.0f, 1.0f);
}

void disarm(const char *why) {
  armed = false; command = 0;
  motor.move(0);
  driver.disable();
  Serial.printf("\n>> DISARMED (%s). Return throttle to zero and send 'g'.\n", why);
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println(F("\n=== E12 hall closed-loop velocity ==="));

  analogReadResolution(12);
  analogSetPinAttenuation(THROTTLE_PIN, ADC_11db);

  sensor.pullup = Pullup::USE_EXTERN;     // board's onboard 4.7k pull-ups
  sensor.init();
  sensor.enableInterrupts(doA, doB, doC);

  driver.voltage_power_supply = SUPPLY_VOLTS;
  driver.voltage_limit        = SUPPLY_VOLTS / 2.0f;
  if (!driver.init()) { Serial.println(F("driver.init() FAILED")); while (1) delay(1000); }

  motor.linkDriver(&driver);
  motor.linkSensor(&sensor);

  motor.foc_modulation    = FOCModulationType::SinePWM;
  motor.torque_controller = TorqueControlType::voltage;
  motor.controller        = MotionControlType::velocity;

  motor.voltage_limit      = VOLTAGE_LIMIT;
  motor.velocity_limit     = MAX_VEL;
  motor.PID_velocity.P     = 0.05f;       // tune these
  motor.PID_velocity.I     = 1.0f;
  motor.PID_velocity.D     = 0.0f;
  motor.PID_velocity.output_ramp = 200.0f;
  motor.LPF_velocity.Tf    = 0.05f;

  motor.useMonitoring(Serial);
  motor.init();

  Serial.println(F("Aligning (wheel must be free to move)..."));
  motor.initFOC();                        // finds zero electrical angle + direction
  driver.disable();

  Serial.printf("zero_electric_angle=%.3f  sensor_direction=%d\n",
                motor.zero_electric_angle, (int)motor.sensor_direction);
  Serial.println(F("Throttle to ZERO, then send 'g' to arm. 'x' disarms."));
  lastLoop = micros();
}

void handleSerial() {
  if (!Serial.available()) return;
  char c = Serial.read();
  if (c == 'g' || c == 'G') {
    if (readThrottle() > 0.02f) { Serial.println(F(">> refused: throttle is not at zero")); return; }
    armed = true; command = 0;
    driver.enable();
    Serial.println(F(">> ARMED"));
  } else if (c == 'x' || c == 'X') {
    disarm("user");
  }
}

void loop() {
  motor.loopFOC();

  unsigned long now = micros();
  float dt = (now - lastLoop) * 1e-6f;
  lastLoop = now;
  if (dt <= 0 || dt > 0.1f) dt = 0.001f;

  handleSerial();

  float want = armed ? readThrottle() * MAX_VEL : 0.0f;
  float step = SLEW_RAD_S2 * dt;
  if (want > command) command = min(want, command + step);
  else                command = max(want, command - step);

  motor.move(command);

  if (millis() - lastPrint > 200) {
    lastPrint = millis();
    Serial.printf("thr %4.2f  cmd %6.2f  vel %6.2f rad/s  (%4.1f km/h)  ang %7.2f  %s\n",
                  readThrottle(), command, motor.shaft_velocity,
                  fabs(motor.shaft_velocity) * 0.1016f * 3.6f,
                  motor.shaft_angle, armed ? "ARMED" : "idle");
  }
}
