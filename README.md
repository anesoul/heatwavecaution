# heatwavecaution

# MoES Heatwave Early Warning System (SIH 2026)

A production-grade, B2G-compliant heatwave monitoring system built for the Ministry of Earth Sciences (MoES). This platform calculates dynamic Mortality Risk Indices (MRI) using hyper-local spatial vulnerability (OSM) and 5-year physiological acclimatization baselines. It features an autonomous background radar using `APScheduler` that automatically routes CAP-compliant emergency webhooks to connected government/NDMA endpoints.

## Prerequisites
* **Python 3** installed on your system.
* **Git** installed.

## Installation & Setup

### 1. Clone the Repository
Open your terminal or command prompt and clone the project:
```bash
git clone https://github.com/anesoul/heatwavecaution.git
cd heatwavecaution
```
### 2. Create a Virtual Environment
Isolating dependencies ensures the app doesn't interfere with other Python projects on your machine.

**For Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```
**For Linux/macOS**
```cmd
python3 -m venv venv:
source venv/bin/activate
```

