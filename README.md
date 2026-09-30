# heatwavecaution - MoES Heatwave Early Warning System (SIH 2026)

A production-grade, B2G-compliant heatwave monitoring system built for the Ministry of Earth Sciences (MoES). This platform calculates dynamic Mortality Risk Indices (MRI) using hyper-local spatial vulnerability (OSM) and 5-year physiological acclimatization baselines. It features an autonomous background radar using `APScheduler` that automatically routes CAP-compliant emergency webhooks to connected government/NDMA endpoints.

## Pre-requisites
* **Python 3.9+** installed on your system.
* **Git** installed.

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/anesoul/heatwavecaution.git
cd heatwavecaution
```
### 2. Create a Virtual Environment
**For Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```
**For Linux/macOS**
```bash
python3 -m venv venv:
source venv/bin/activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Run Program
```bash
flask run
```
The terminal will boot up the Flask server at http://127.0.0.1:5000/

