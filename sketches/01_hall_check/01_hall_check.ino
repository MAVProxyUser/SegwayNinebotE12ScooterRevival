/*
 * 01_hall_check  --  Ninebot E12 hub motor, Hall sensor sanity test
 *
 * NO MOTOR POWER NEEDED. Phase wires stay disconnected for this sketch.
 * Goal: prove the 3 Hall sensors work, learn the state sequence, and
 * measure POLE_PAIRS (which every later sketch depends on).
 *
 * Wiring:
 *   Hall +5V  -> ESP32 VUSB/5V rail (NOT 3V3 -- most SS41-style halls are
 *                unreliable below ~4V)
 *   Hall GND  -> ESP32 GND  (common ground, mandatory)
 *   Hall A/B/C-> H_A/H_B/H_C below, each with a 4.7k pull-up to 3V3.
 *
 * Hub-motor halls are almost always OPEN-COLLECTOR, so pulling up to 3V3
 * gives you 3.3V logic even though the sensor is powered from 5V.
 * VERIFY THIS FIRST with a meter: with only 5V+GND connected and a 4.7k
 * pull-up to 3V3 on one output, the output must swing 0V <-> ~3.3V as you
 * turn the wheel. If it swings 0 <-> 5V it is a push-pull output and you
 * need a level shifter or a divider before touching the ESP32.
 */

#define H_A 13
#define H_B 14
#define H_C 4

// Legal Hall states are 1..6. 0 and 7 mean a dead sensor or bad wiring.
static const char *STATE_NAME[8] = {
  "000 ILLEGAL", "001", "010", "011", "100", "101", "110", "111 ILLEGAL"
};

uint8_t  lastState   = 0xFF;
long     transitions = 0;
long     netSteps    = 0;      // +1 forward, -1 reverse
long     illegalHits = 0;

// Forward 6-step order for a 120-degree hall layout: 1,3,2,6,4,5 (repeats)
int8_t stepDelta(uint8_t from, uint8_t to) {
  static const uint8_t fwd[8] = {0, 3, 6, 2, 5, 1, 4, 0}; // fwd[state] = next state
  if (from > 6 || to > 6 || from == 0 || to == 0) return 0;
  if (fwd[from] == to) return  1;
  if (fwd[to] == from) return -1;
  return 0;  // skipped a state -- too fast, or a flaky sensor
}

uint8_t readHalls() {
  return (digitalRead(H_A) << 2) | (digitalRead(H_B) << 1) | digitalRead(H_C);
}

void printBanner() {
  Serial.println();
  Serial.println(F("=== E12 Hall check ==="));
  Serial.println(F("1) Turn the wheel SLOWLY by hand. You should see states"));
  Serial.println(F("   cycling through 1,3,2,6,4,5 (or the reverse) and never 0 or 7."));
  Serial.println(F("2) Mark the tire and the fork with a pen so you can hit the"));
  Serial.println(F("   same spot exactly."));
  Serial.println(F("3) Send 'z' to zero the counter, turn EXACTLY one full wheel"));
  Serial.println(F("   revolution, then send 'p' to print the result."));
  Serial.println(F("   pole_pairs = transitions / 6"));
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(500);

  // Internal pull-ups as a backstop. GPIO34-39 have NO internal pull-ups,
  // so if you move these pins there the external 4.7k resistors are required.
  pinMode(H_A, INPUT_PULLUP);
  pinMode(H_B, INPUT_PULLUP);
  pinMode(H_C, INPUT_PULLUP);

  printBanner();
  lastState = readHalls();
  Serial.printf("start state = %u (%s)\n", lastState, STATE_NAME[lastState]);
}

void loop() {
  uint8_t s = readHalls();

  if (s != lastState) {
    delayMicroseconds(300);           // crude debounce
    if (readHalls() == s) {
      transitions++;
      int8_t d = stepDelta(lastState, s);
      netSteps += d;

      if (s == 0 || s == 7) {
        illegalHits++;
        Serial.printf("!! state %u %s  <-- dead hall or broken wire\n", s, STATE_NAME[s]);
      } else {
        Serial.printf("state %u (%s)  dir %+d   transitions %ld   net %ld   est pole_pairs %.2f\n",
                      s, STATE_NAME[s], d, transitions, netSteps, transitions / 6.0);
      }
      lastState = s;
    }
  }

  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'z' || c == 'Z') {
      transitions = 0; netSteps = 0; illegalHits = 0;
      Serial.println(F(">> counters zeroed. Turn exactly ONE revolution, then send 'p'."));
    } else if (c == 'p' || c == 'P') {
      Serial.println();
      Serial.printf(">> transitions=%ld  net=%ld  illegal=%ld\n", transitions, netSteps, illegalHits);
      Serial.printf(">> POLE_PAIRS = %ld / 6 = %.2f  (expect a whole number, commonly 15)\n",
                    transitions, transitions / 6.0);
      Serial.println(F(">> Write that number into the other two sketches."));
      Serial.println();
    } else if (c == 'h' || c == 'H') {
      printBanner();
    }
  }
}
