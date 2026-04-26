/*
 * ============================================================
 *   ENERGYGURU – POWER CALCULUS
 *   Arduino Energy Monitor for City Model
 * ============================================================
 *   Sensors : ACS712 Current Sensor (A0)
 *             Voltage Divider       (A1)
 *   Output  : Serial CSV → Python Streamlit Dashboard
 * ============================================================
 *   CSV Format (every 1 s):
 *   voltage, current, power_W, energy_kWh,
 *   bill_pkr, carbon_kg, runtime_hrs
 * ============================================================
 */

// ── Pin Definitions ──────────────────────────────────────────
const int CURRENT_PIN  = A0;   // ACS712 output
const int VOLTAGE_PIN  = A1;   // Voltage divider output

// ── ACS712 Calibration ────────────────────────────────────────
// Change sensitivity based on your module variant:
//   ACS712-5A  → 0.185
//   ACS712-20A → 0.100
//   ACS712-30A → 0.066
const float ACS_SENSITIVITY = 0.185;  // V per Ampere
const float VCC              = 5.0;   // Arduino supply (V)
const float ADC_STEPS        = 1023.0;

// ── Voltage Divider Calibration ──────────────────────────────
// R1 = 10 kΩ , R2 = 1 kΩ → ratio = (R1+R2)/R2 = 11
// Adjust this ratio if you measure differently.
const float VD_RATIO = 11.0;

// ── Tariff & Carbon Constants ────────────────────────────────
const float RATE_PKR_PER_KWH  = 50.0;   // Electricity tariff (PKR)
const float CARBON_KG_PER_KWH = 0.82;   // Pakistan grid carbon factor

// ── Runtime Variables ────────────────────────────────────────
float    totalEnergy_kWh = 0.0;
unsigned long lastSampleMs = 0;
unsigned long startMs      = 0;
const int     SAMPLES      = 150;  // samples per RMS reading

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  lastSampleMs = millis();
  startMs      = millis();

  // Header so Python knows the Arduino is ready
  Serial.println("ENERGYGURU_START");
  Serial.println("voltage,current,power_w,energy_kwh,bill_pkr,carbon_kg,runtime_hrs");
}

// ─────────────────────────────────────────────────────────────
// Read RMS current from ACS712
// The sensor outputs VCC/2 when current = 0 A
// ─────────────────────────────────────────────────────────────
float readCurrentRMS() {
  float sumSq = 0.0;
  for (int i = 0; i < SAMPLES; i++) {
    int   raw      = analogRead(CURRENT_PIN);
    float pinV     = (raw / ADC_STEPS) * VCC;
    float current  = (pinV - VCC / 2.0) / ACS_SENSITIVITY;
    sumSq += current * current;
    delayMicroseconds(80);
  }
  float rms = sqrt(sumSq / SAMPLES);
  // Noise floor: ignore < 0.05 A (sensor idle noise)
  return (rms < 0.05) ? 0.0 : rms;
}

// ─────────────────────────────────────────────────────────────
// Read RMS voltage via voltage divider
// Divider scales mains voltage down to 0–5 V range
// ─────────────────────────────────────────────────────────────
float readVoltageRMS() {
  float sumSq = 0.0;
  for (int i = 0; i < SAMPLES; i++) {
    int   raw   = analogRead(VOLTAGE_PIN);
    float pinV  = (raw / ADC_STEPS) * VCC;
    float measV = pinV * VD_RATIO;
    sumSq += measV * measV;
    delayMicroseconds(80);
  }
  return sqrt(sumSq / SAMPLES);
}

// ─────────────────────────────────────────────────────────────
void loop() {
  // ── 1. Read sensors ────────────────────────────────────────
  float current_A = readCurrentRMS();
  float voltage_V = readVoltageRMS();

  // ── 2. Instantaneous power ─────────────────────────────────
  float power_W  = voltage_V * current_A;
  float power_kW = power_W / 1000.0;

  // ── 3. Energy accumulation (trapezoidal, 1-s interval) ─────
  unsigned long now        = millis();
  float         dt_hours   = (now - lastSampleMs) / 3600000.0;
  lastSampleMs             = now;
  totalEnergy_kWh         += power_kW * dt_hours;

  // ── 4. Derived values ──────────────────────────────────────
  float bill_pkr   = totalEnergy_kWh * RATE_PKR_PER_KWH;
  float carbon_kg  = totalEnergy_kWh * CARBON_KG_PER_KWH;
  float runtime_h  = (now - startMs) / 3600000.0;

  // ── 5. Send CSV over Serial ────────────────────────────────
  Serial.print(voltage_V,  2);  Serial.print(",");
  Serial.print(current_A,  3);  Serial.print(",");
  Serial.print(power_W,    2);  Serial.print(",");
  Serial.print(totalEnergy_kWh, 6); Serial.print(",");
  Serial.print(bill_pkr,   4);  Serial.print(",");
  Serial.print(carbon_kg,  6);  Serial.print(",");
  Serial.println(runtime_h, 5);

  delay(1000);   // 1-second sampling rate
}
