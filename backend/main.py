"""
FastAPI Backend for Sedentary Activity Tracker
Main application with REST API endpoints
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
import threading
import time

from config import API_HOST, API_PORT
from database import init_db, get_db, SessionLocal, SensorReadingDB, AlertEventDB
from models import (
    SensorReading, ProcessedReading, CurrentStatus, 
    SessionStats, TimelineDataPoint, ActivityState
)
from data_processor import DataProcessor
from serial_reader import get_serial_reader, SerialReader


# Global instances
data_processor = DataProcessor()
serial_reader: Optional[SerialReader] = None


def process_and_store_reading(reading: SensorReading):
    """
    Callback function to process and store each reading.
    Called by the serial reader for each new reading.
    """
    # Process the reading
    processed = data_processor.process_reading(reading)
    
    # Store in database
    db = SessionLocal()
    try:
        db_reading = SensorReadingDB(
            timestamp=processed.timestamp,
            pir=processed.pir,
            delta_mag=processed.delta_mag,
            delta_mag_smoothed=processed.delta_mag_smoothed,
            inactive_seconds=processed.inactive_seconds,
            alerted=processed.alerted,
            activity_state=processed.activity_state.value,
            confidence=processed.confidence
        )
        db.add(db_reading)
        
        # If this is an alert, store the alert event
        if processed.alerted == 1:
            # Check if we already have this alert (within last 5 seconds)
            recent_alert = db.query(AlertEventDB).filter(
                AlertEventDB.timestamp >= processed.timestamp - timedelta(seconds=5)
            ).first()
            
            if not recent_alert:
                alert_event = AlertEventDB(
                    timestamp=processed.timestamp,
                    duration_seconds=processed.inactive_seconds
                )
                db.add(alert_event)
        
        db.commit()
    except Exception as e:
        print(f"Error storing reading: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global serial_reader
    
    # Startup
    print("Starting Sedentary Activity Tracker Backend...")
    init_db()
    
    # Initialize serial reader
    serial_reader = get_serial_reader()
    serial_reader.set_callback(process_and_store_reading)
    
    # Try to connect to serial port
    if serial_reader.connect():
        serial_reader.start_reading()
        print("Serial reading started successfully!")
    else:
        print("WARNING: Could not connect to serial port. Running without live data.")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    if serial_reader:
        serial_reader.stop_reading()


# Create FastAPI app
app = FastAPI(
    title="Sedentary Activity Tracker API",
    description="Backend API for monitoring sedentary behavior using sensor data",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    """Root endpoint - API status"""
    return {
        "status": "running",
        "name": "Sedentary Activity Tracker API",
        "version": "1.0.0",
        "serial_connected": serial_reader.is_running if serial_reader else False
    }


@app.get("/api/status", response_model=CurrentStatus)
def get_current_status():
    """
    Get current activity status.
    Returns real-time status including activity state, inactive seconds, and alert status.
    """
    return data_processor.get_current_status()


@app.get("/api/stats", response_model=SessionStats)
def get_session_stats():
    """
    Get session statistics.
    Returns total readings, active/inactive time, longest inactive period, and alert count.
    """
    return data_processor.get_session_stats()


@app.get("/api/readings/recent", response_model=List[ProcessedReading])
from utils import to_berlin

def get_recent_readings(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get recent sensor readings.
    Returns the most recent processed readings from the database.
    """
    readings = db.query(SensorReadingDB).order_by(
        SensorReadingDB.timestamp.desc()
    ).limit(limit).all()
    
    return [
        ProcessedReading(
            id=r.id,
            timestamp=to_berlin(r.timestamp),
            pir=r.pir,
            delta_mag=r.delta_mag,
            delta_mag_smoothed=r.delta_mag_smoothed,
            inactive_seconds=r.inactive_seconds,
            alerted=r.alerted,
            activity_state=ActivityState(r.activity_state),
            confidence=r.confidence
        )
        for r in reversed(readings)  # Return in chronological order
    ]


@app.get("/api/timeline", response_model=List[TimelineDataPoint])
def get_timeline_data(
    minutes: int = 60,
    db: Session = Depends(get_db)
):
    """
    Get timeline data for visualization.
    Returns activity states over time for the specified number of minutes.
    """
    since = datetime.now() - timedelta(minutes=minutes)
    
    readings = db.query(SensorReadingDB).filter(
        SensorReadingDB.timestamp >= since
    ).order_by(SensorReadingDB.timestamp.asc()).all()
    
    return [
        TimelineDataPoint(
            timestamp=to_berlin(r.timestamp),
            activity_state=ActivityState(r.activity_state),
            delta_mag=r.delta_mag,
            inactive_seconds=r.inactive_seconds
        )
        for r in readings
    ]


@app.get("/api/alerts", response_model=List[dict])
def get_alert_events(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get recent sedentary alert events.
    """
    alerts = db.query(AlertEventDB).order_by(
        AlertEventDB.timestamp.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": a.id,
            "timestamp": to_berlin(a.timestamp),
            "duration_seconds": a.duration_seconds
        }
        for a in alerts
    ]


@app.get("/api/daily-summary")
def get_daily_summary(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get daily summary statistics.
    If no date provided, returns today's summary.
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date()
    
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    readings = db.query(SensorReadingDB).filter(
        SensorReadingDB.timestamp >= start_of_day,
        SensorReadingDB.timestamp <= end_of_day
    ).all()
    
    alerts = db.query(AlertEventDB).filter(
        AlertEventDB.timestamp >= start_of_day,
        AlertEventDB.timestamp <= end_of_day
    ).all()
    
    if not readings:
        return {
            "date": str(target_date),
            "total_readings": 0,
            "active_seconds": 0,
            "inactive_seconds": 0,
            "active_percentage": 0,
            "alert_count": 0,
            "longest_inactive_period": 0
        }
    
    active_count = sum(1 for r in readings if r.activity_state == "active")
    inactive_count = sum(1 for r in readings if r.activity_state != "active")
    max_inactive = max((r.inactive_seconds for r in readings), default=0)
    
    total = len(readings)
    active_pct = (active_count / total * 100) if total > 0 else 0
    
    return {
        "date": str(target_date),
        "total_readings": total,
        "active_seconds": active_count,
        "inactive_seconds": inactive_count,
        "active_percentage": round(active_pct, 2),
        "alert_count": len(alerts),
        "longest_inactive_period": max_inactive
    }


@app.post("/api/reset-stats")
def reset_session_stats():
    """Reset the current session statistics"""
    data_processor.reset_stats()
    return {"message": "Session statistics reset successfully"}


@app.get("/api/serial/status")
def get_serial_status():
    """Get serial connection status"""
    if serial_reader:
        return {
            "connected": serial_reader.is_running,
            "port": serial_reader.port,
            "baud_rate": serial_reader.baud_rate,
            "recent_readings_count": len(serial_reader.recent_readings)
        }
    return {"connected": False, "error": "Serial reader not initialized"}


@app.post("/api/serial/reconnect")
def reconnect_serial():
    """Attempt to reconnect to serial port"""
    global serial_reader
    
    if serial_reader:
        serial_reader.stop_reading()
        time.sleep(1)
        
        if serial_reader.connect():
            serial_reader.start_reading()
            return {"success": True, "message": "Reconnected successfully"}
        else:
            return {"success": False, "message": "Failed to reconnect"}
    
    return {"success": False, "message": "Serial reader not initialized"}


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("Sedentary Activity Tracker - Backend Server")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
