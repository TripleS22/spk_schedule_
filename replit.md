# Modul Analisis Logistik Otomatis

## Overview
Sistem optimasi penugasan unit transportasi ke jadwal rute harian. Aplikasi ini menggunakan algoritma multi-kriteria untuk menghasilkan penugasan optimal berdasarkan kapasitas, jarak, ketersediaan, dan biaya operasional.

## Current State
- **Status**: MVP Complete
- **Last Updated**: December 2024
- **Framework**: Streamlit + Python

## Project Architecture

### File Structure
```
├── app.py                    # Main Streamlit application with UI components
├── data_models.py            # Data structures and sample data
├── optimization_engine.py    # Multi-criteria optimization algorithm
├── .streamlit/config.toml    # Streamlit server configuration
└── replit.md                 # Project documentation
```

### Core Components

**1. Data Models (data_models.py)**
- `Unit`: Armada transportasi dengan kapasitas, efisiensi BBM, biaya operasional
- `Route`: Rute perjalanan dengan jarak, waktu tempuh, kebutuhan kapasitas
- `Schedule`: Jadwal keberangkatan dengan hari operasi dan prioritas
- `OperationalParameters`: Parameter operasional (turnaround, istirahat, harga BBM)

**2. Optimization Engine (optimization_engine.py)**
- Multi-criteria scoring dengan 4 dimensi: kapasitas, jarak, ketersediaan, biaya
- Constraint validation: pengecekan izin rute, kapasitas minimum, status unit
- Conflict detection: pencegahan tumpang tindih penugasan
- Metrics calculation: tingkat cakupan, utilisasi, biaya total

**3. Main Application (app.py)**
- Dashboard: ringkasan operasional dengan visualisasi
- Data Management: CRUD untuk unit, rute, dan jadwal
- Optimization: antarmuka untuk menjalankan algoritma optimasi
- Reports: analisis performa unit dan rute
- Settings: konfigurasi parameter operasional

### Algorithm Details

**Scoring Formula:**
```
Total Score = (0.25 × Capacity Score) + (0.20 × Distance Score) + 
              (0.30 × Availability Score) + (0.25 × Cost Score)
```

**Cycle Time Calculation:**
```
Cycle Time = (Route Time × 2) + Turnaround Time
```

**Fuel Cost Calculation:**
```
Fuel Cost = (Distance × 2 / Fuel Efficiency) × Fuel Price
```

## Dependencies
- streamlit: Web application framework
- pandas: Data manipulation
- numpy: Numerical computations
- plotly: Interactive visualizations
- scipy: Scientific computing

## Running the Application
```bash
streamlit run app.py --server.port 5000
```

## User Preferences
- Language: Indonesian (Bahasa Indonesia)
- UI Theme: Default Streamlit theme
- Data Format: Indonesian currency (Rp), metric system (km)

## Recent Changes
- December 2024: Initial MVP implementation
  - Complete data models for logistics entities
  - Multi-criteria optimization engine
  - Full dashboard with 7 navigation pages
  - Interactive visualizations with Plotly
  - Sample data for demonstration
