# ⚡ ENERGYGURU – POWER CALCULUS
### AI-Assisted City Energy Monitor  |  Arduino + Python Streamlit

---

## 📁 Project Structure

```
energyguru/
├── arduino_energy_monitor/
│   └── arduino_energy_monitor.ino    ← Upload to Arduino Uno
└── energyguru_dashboard/
    ├── dashboard.py                   ← Streamlit Dashboard
    ├── requirements.txt
    └── README.md                      ← This file
```

---

## 🔧 PATH 1 — HARDWARE (Arduino City Model)

### Components Required
| Component | Qty | Notes |
|-----------|-----|-------|
| Arduino Uno | 1 | Any clone works |
| ACS712-5A Current Sensor | 1 | or 20A for higher loads |
| Voltage Divider Module | 1 | or build: 10 kΩ + 1 kΩ |
| USB Cable (Type-B) | 1 | Arduino to Computer |
| City model appliances | — | LEDs, small motors, bulbs |
| Connecting wires | — | Jumper wires |

### Wiring
```
ACS712 Module          Arduino Uno
──────────────         ───────────
VCC        ──────────► 5V
GND        ──────────► GND
OUT        ──────────► A0  (CURRENT_PIN)

Voltage Divider        Arduino Uno
───────────────        ───────────
VCC        ──────────► City model power rail (+)
GND        ──────────► City model power rail (-)
Output     ──────────► A1  (VOLTAGE_PIN)

Note: Voltage divider output must NOT exceed 5V.
      For 12V city model: R1=22kΩ, R2=3.3kΩ → ratio ≈ 7.7
      Update VD_RATIO in the .ino file to match your resistors.
```

### Uploading Arduino Code
1. Open **Arduino IDE**
2. Open `arduino_energy_monitor.ino`
3. Adjust constants at the top of the file if needed:
   - `ACS_SENSITIVITY` — see label on your ACS712 module
   - `VD_RATIO` — calculate based on your resistor values
   - `RATE_PKR_PER_KWH` — your local electricity tariff
4. Select **Board: Arduino Uno** and the correct **COM port**
5. Click **Upload**
6. Open **Serial Monitor** at 9600 baud to verify CSV output

### Expected Serial Output
```
ENERGYGURU_START
voltage,current,power_w,energy_kwh,bill_pkr,carbon_kg,runtime_hrs
219.87,1.234,271.42,0.000075,0.003752,0.000062,0.00028
220.12,1.256,276.47,0.000152,0.007591,0.000125,0.00056
...
```

---

## 💻 PATH 2 — SOFTWARE (Python Streamlit Dashboard)

### Requirements
- Python 3.9 or higher
- Internet connection (for map tiles)

### Installation
```bash
# 1. Clone or copy the energyguru_dashboard folder

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run dashboard.py
```
The app opens automatically at: **http://localhost:8501**

---

## 🖥️ Dashboard Features

### Tab 1 — ⚡ Live Dashboard
- 6 real-time metric cards (Voltage, Current, Power, Energy, Bill, CO₂)
- 3 animated gauge dials
- Dual-axis live voltage/current chart
- Power area chart (live, 500-point rolling window)

### Tab 2 — 🗺️ City Map
- Interactive OpenStreetMap (no API key needed)
- Coverage ring showing the monitored zone
- Live readings panel alongside the map
- Voltage health status indicator

### Tab 3 — 📈 Analytics
- Statistical summary (mean, σ, min, max)
- Energy accumulation area chart
- Bill + CO₂ dual-axis trend chart
- Power distribution histogram
- **AI prediction** — linear regression forecasts next 60 seconds;
  extrapolates to daily/monthly energy & cost estimates
- Scrollable data table (last 50 readings)
- CSV export button

### Tab 4 — 📄 Report
- Fill in: title, institution, operator, notes
- Click **Generate PDF Report** to create a dark-themed PDF
- PDF contains:
  1. Measurement Summary table
  2. Arduino calculation formulas with actual values
  3. Last 20 readings table
  4. AI energy recommendations
  5. Notes section
- Download button to save PDF locally

---

## ⚙️ Sidebar Settings

| Setting | Description |
|---------|-------------|
| 🎮 Demo Mode | Simulates city-model data without hardware |
| Serial Port | Select Arduino COM port (Windows: COM3, Linux: /dev/ttyUSB0) |
| Baud Rate | Must match Arduino sketch (default 9600) |
| Tariff PKR/kWh | Your local electricity price |
| Carbon Factor | kg CO₂ per kWh (Pakistan grid ≈ 0.82) |
| City Location | Pre-loaded or custom lat/lon |

---

## 🎮 Demo Mode (No Hardware Needed)

Toggle **Demo Mode** ON in the sidebar to see simulated city-model data.
- Voltage: ~220 V with realistic fluctuation
- Current: 0.8–2.8 A (simulates city appliances cycling)
- All calculations, charts, and PDF report work in demo mode

---

## 🔌 Connecting Arduino to Dashboard

1. Plug Arduino into computer via USB
2. In the sidebar: turn **Demo Mode OFF**
3. Select the correct **Serial Port** (check Arduino IDE → Tools → Port)
4. Click **▶ Connect**
5. Status shows **◉ ARDUINO CONNECTED** when live

---

## 🇵🇰 Pakistan-Specific Defaults

| Parameter | Value | Source |
|-----------|-------|--------|
| Tariff | PKR 50 / kWh | NEPRA average 2024 |
| Carbon Factor | 0.82 kg CO₂/kWh | Pakistan national grid |
| Default City | Rawalpindi | Adjustable |

---

## 📚 Technologies Used

**Hardware:** Arduino Uno, ACS712, Voltage Divider
**Software:** Python, Streamlit, Plotly, Pandas, NumPy, PySerial, fpdf2
**AI/ML:** Linear Regression (energy prediction)
**Maps:** OpenStreetMap via Plotly Mapbox (free, no API key)
**Report:** fpdf2 (free PDF generation)

---

## 🎓 Educational Topics Covered

- IoT sensor integration (Arduino + Python)
- Signal processing (RMS calculation)
- Data logging and time-series analysis
- Machine learning (linear regression for prediction)
- Data visualization (Plotly, Streamlit)
- Sustainability & carbon footprint calculation
- PDF report generation

---

*EnergyGuru Power Calculus — ENERGYGURU-2025*
