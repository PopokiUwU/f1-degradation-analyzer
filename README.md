# F1 Tyre Degradation Analysis 🏎️📊

Advanced Python tool built with **FastF1**, **Pandas**, and **NumPy** designed to analyze and calculate real-time tyre degradation rates during Formula 1 Grand Prix sessions.

## Features
- **Fuel Mass Correction:** Accounts for fuel weight sensitivity (`0.032 s/kg`) and dynamic fuel burn during safety cars/neutralizations.
- **Track Evolution Normalization:** Dynamically detects baseline conditions and normalizes lap times against track evolution.
- **Robust Data Cleaning:** 
  - Automatically filters out pit stops, VSC/SC periods (`TrackStatus` 4, 5, 6, 7), and wet/intermediate weather tyres.
  - Excludes warm-up laps (`StintLap > 3`) to focus on steady-state degradation.
- **Anomaly Detection:** Uses neighbor differentials (`IsSigWor`) to strip out traffic anomalies and sudden time spikes.
- **Physical Validation:** Enforces physical constraints via linear regression (`safe_polyfit`) to discard non-sensical negative degradation and short, unreliable stints.

## Prerequisites
Make sure you have Python installed along with the required libraries:
```bash
pip install fastf1 pandas numpy matplotlib
