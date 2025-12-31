"""
Data processing and activity classification logic
"""

from collections import deque
from datetime import datetime
from typing import Optional, List
from models import SensorReading, ProcessedReading, ActivityState, CurrentStatus, SessionStats
from config import (
    DELTA_MAG_ACTIVE_THRESHOLD,
    DELTA_MAG_TRANSITION_THRESHOLD,
    MOVING_AVERAGE_WINDOW,
    SEDENTARY_THRESHOLD_SECONDS
)


class DataProcessor:
    """
    Processes raw sensor data and classifies activity state.
    Implements smoothing, sensor fusion, and activity classification.
    """

    def __init__(self):
        # Buffer for moving average smoothing
        self.delta_mag_buffer: deque = deque(maxlen=MOVING_AVERAGE_WINDOW)
        
        # Track current status
        self.last_movement_time: Optional[datetime] = None
        self.current_inactive_seconds: int = 0
        self.is_alerted: bool = False
        
        # Statistics tracking
        self.total_readings: int = 0
        self.total_active_readings: int = 0
        self.total_inactive_readings: int = 0
        self.alert_count: int = 0
        self.longest_inactive_period: int = 0
        self.current_inactive_streak: int = 0

    def apply_moving_average(self, delta_mag: float) -> float:
        """
        Apply moving average smoothing to delta magnitude.
        This reduces noise from sensor readings.
        """
        self.delta_mag_buffer.append(delta_mag)
        
        if len(self.delta_mag_buffer) == 0:
            return delta_mag
        
        return sum(self.delta_mag_buffer) / len(self.delta_mag_buffer)

    def classify_activity(self, pir: int, delta_mag_smoothed: float) -> tuple[ActivityState, float]:
        """
        Classify activity state using sensor fusion.
        
        Returns:
            tuple: (ActivityState, confidence score 0.0-1.0)
        
        Logic:
        - ACTIVE: PIR detects motion OR high accelerometer change
        - TRANSITION: Medium accelerometer change, no PIR
        - INACTIVE: Low accelerometer change AND no PIR
        
        Confidence:
        - High (0.9-1.0): Both sensors agree
        - Medium (0.6-0.8): Only one sensor indicates movement
        - Low (0.4-0.5): Borderline readings
        """
        pir_motion = pir == 1
        
        # High movement detected
        if delta_mag_smoothed >= DELTA_MAG_ACTIVE_THRESHOLD:
            if pir_motion:
                # Both sensors agree - high confidence active
                return ActivityState.ACTIVE, 1.0
            else:
                # Only accelerometer - medium-high confidence
                return ActivityState.ACTIVE, 0.8
        
        # Medium movement
        elif delta_mag_smoothed >= DELTA_MAG_TRANSITION_THRESHOLD:
            if pir_motion:
                # PIR confirms some movement
                return ActivityState.ACTIVE, 0.7
            else:
                # Minor movement, could be transition
                return ActivityState.TRANSITION, 0.6
        
        # Low movement from accelerometer
        else:
            if pir_motion:
                # PIR detects motion but accelerometer doesn't
                # Could be large slow movement
                return ActivityState.ACTIVE, 0.6
            else:
                # Both sensors agree - inactive
                return ActivityState.INACTIVE, 0.9

    def process_reading(self, reading: SensorReading) -> ProcessedReading:
        """
        Process a raw sensor reading and return classified result.
        """
        # Apply smoothing
        delta_mag_smoothed = self.apply_moving_average(reading.delta_mag)
        
        # Classify activity
        activity_state, confidence = self.classify_activity(
            reading.pir, 
            delta_mag_smoothed
        )
        
        # Update statistics
        self.total_readings += 1
        
        if activity_state == ActivityState.ACTIVE:
            self.total_active_readings += 1
            self.last_movement_time = reading.timestamp
            self.current_inactive_streak = 0
            self.is_alerted = False
        else:
            self.total_inactive_readings += 1
            self.current_inactive_streak += 1
            
            # Track longest inactive period
            if reading.inactive_seconds > self.longest_inactive_period:
                self.longest_inactive_period = reading.inactive_seconds
        
        # Track alerts
        if reading.alerted == 1 and not self.is_alerted:
            self.alert_count += 1
            self.is_alerted = True
        
        self.current_inactive_seconds = reading.inactive_seconds
        
        return ProcessedReading(
            timestamp=reading.timestamp,
            pir=reading.pir,
            delta_mag=reading.delta_mag,
            delta_mag_smoothed=delta_mag_smoothed,
            inactive_seconds=reading.inactive_seconds,
            alerted=reading.alerted,
            activity_state=activity_state,
            confidence=confidence
        )

    def get_current_status(self) -> CurrentStatus:
        """Get current activity status for real-time display"""
        # Determine current activity state based on recent data
        if self.current_inactive_seconds >= SEDENTARY_THRESHOLD_SECONDS:
            activity_state = ActivityState.INACTIVE
        elif len(self.delta_mag_buffer) > 0:
            avg_delta = sum(self.delta_mag_buffer) / len(self.delta_mag_buffer)
            if avg_delta >= DELTA_MAG_ACTIVE_THRESHOLD:
                activity_state = ActivityState.ACTIVE
            elif avg_delta >= DELTA_MAG_TRANSITION_THRESHOLD:
                activity_state = ActivityState.TRANSITION
            else:
                activity_state = ActivityState.INACTIVE
        else:
            activity_state = ActivityState.INACTIVE
        
        return CurrentStatus(
            activity_state=activity_state,
            inactive_seconds=self.current_inactive_seconds,
            is_alerted=self.is_alerted,
            last_movement=self.last_movement_time or datetime.now(),
            confidence=0.9 if self.total_readings > MOVING_AVERAGE_WINDOW else 0.5
        )

    def get_session_stats(self) -> SessionStats:
        """Get statistics for the current session"""
        if self.total_readings == 0:
            return SessionStats(
                total_readings=0,
                total_active_time_seconds=0,
                total_inactive_time_seconds=0,
                longest_inactive_period_seconds=0,
                alert_count=0,
                active_percentage=0.0
            )
        
        active_percentage = (self.total_active_readings / self.total_readings) * 100
        
        return SessionStats(
            total_readings=self.total_readings,
            total_active_time_seconds=self.total_active_readings,  # 1 reading per second
            total_inactive_time_seconds=self.total_inactive_readings,
            longest_inactive_period_seconds=self.longest_inactive_period,
            alert_count=self.alert_count,
            active_percentage=round(active_percentage, 2)
        )

    def reset_stats(self):
        """Reset all statistics (for new session)"""
        self.delta_mag_buffer.clear()
        self.last_movement_time = None
        self.current_inactive_seconds = 0
        self.is_alerted = False
        self.total_readings = 0
        self.total_active_readings = 0
        self.total_inactive_readings = 0
        self.alert_count = 0
        self.longest_inactive_period = 0
        self.current_inactive_streak = 0
