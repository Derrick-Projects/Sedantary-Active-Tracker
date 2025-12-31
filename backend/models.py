"""
Data models for the Sedentary Activity Tracker
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class ActivityState(str, Enum):
    """Activity classification states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSITION = "transition"


class SensorReading(BaseModel):
    """Raw sensor reading from Arduino"""
    timestamp: datetime
    pir: int  # 0 or 1
    delta_mag: float  # Change in acceleration magnitude
    inactive_seconds: int  # Seconds since last movement
    alerted: int  # 0 or 1 - whether sedentary alert was triggered


class ProcessedReading(BaseModel):
    """Processed sensor reading with activity classification"""
    id: Optional[int] = None
    timestamp: datetime
    pir: int
    delta_mag: float
    delta_mag_smoothed: float
    inactive_seconds: int
    alerted: int
    activity_state: ActivityState
    confidence: float  # 0.0 to 1.0


class SedentaryAlert(BaseModel):
    """Sedentary alert event"""
    id: Optional[int] = None
    timestamp: datetime
    duration_seconds: int  # How long they were inactive when alert triggered


class CurrentStatus(BaseModel):
    """Current activity status for real-time display"""
    activity_state: ActivityState
    inactive_seconds: int
    is_alerted: bool
    last_movement: datetime
    confidence: float


class SessionStats(BaseModel):
    """Statistics for a session or time period"""
    total_readings: int
    total_active_time_seconds: int
    total_inactive_time_seconds: int
    longest_inactive_period_seconds: int
    alert_count: int
    active_percentage: float


class TimelineDataPoint(BaseModel):
    """Data point for timeline visualization"""
    timestamp: datetime
    activity_state: ActivityState
    delta_mag: float
    inactive_seconds: int
