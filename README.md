# Sedentary Activity Tracker

## Project Overview

The Sedentary Activity Tracker is a real-time system designed to monitor human sedentary behavior—periods of physical inactivity—and trigger alerts when inactivity exceeds a set threshold. It combines data from multiple sensors and accurate timing to reliably distinguish between stillness and movement.

### Problem Tackled
Modern lifestyles often involve long periods of sitting or inactivity, which can negatively impact health. This project aims to:
- Detect when a person has been inactive for too long
- Provide real-time feedback and alerts
- Help users become more aware of their sedentary habits

### Solution
The system uses sensor fusion and time tracking to classify activity states and alert users when they are sedentary for too long. It features:
- **MPU6050 Accelerometer/Gyroscope**: Detects subtle body movements
- **HC-SR501 PIR Motion Sensor**: Detects larger body movements
- **DS3231 Real-Time Clock (RTC)**: Provides accurate timestamps
- **Backend (Python + FastAPI + PostgreSQL)**: Processes, stores, and exposes sensor data via REST API
- **Frontend (D3.js Dashboard)**: Visualizes activity status, timelines, acceleration, and alerts

## Features
- Real-time activity classification (Active, Inactive, Transition)
- Inactivity duration tracking and alerting
- Sensor fusion for robust detection
- Data smoothing and noise filtering
- REST API for data access
- Interactive dashboard with D3.js visualizations
- All times displayed in Berlin timezone

## Installation & Setup

### 1. Hardware
- Connect Arduino with MPU6050, PIR sensor, and DS3231 RTC
- Upload the provided Arduino code (`main_arduino.ino`)

### 2. Backend (Python)
- Install Python 3.11+ (recommended)
- Install PostgreSQL and create a database named `sedentary_tracker`
- Clone this repository
- Install dependencies:

```bash
cd backend
py -m pip install -r requirements.txt
```

- Update `config.py` with your PostgreSQL credentials (default user: `postgres`, password: `root`)
- Initialize the database tables:

```bash
py database.py
```

- Start the backend server:

```bash
py -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Frontend (Dashboard)
- Start a simple HTTP server in the `frontend` folder:

```bash
cd ../frontend
py -m http.server 3000
```

- Open your browser at [http://localhost:3000](http://localhost:3000)

## Usage
- The dashboard will show real-time status, inactivity timer, activity timeline, acceleration graph, session summary, and alert history.
- All times are shown in Berlin timezone.
- Alerts are triggered after 20 seconds of inactivity (for testing).


