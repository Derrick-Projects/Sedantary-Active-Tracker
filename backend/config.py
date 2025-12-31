"""
Configuration settings for the Sedentary Activity Tracker
"""

# Serial port configuration
SERIAL_PORT = "COM9"
BAUD_RATE = 9600

# Sedentary detection thresholds
SEDENTARY_THRESHOLD_SECONDS = 20  # Alert after 20 seconds of inactivity
MOVEMENT_THRESHOLD = 0.5  # m/s² - matches Arduino setting

# Activity classification thresholds
DELTA_MAG_ACTIVE_THRESHOLD = 0.5      # Above this = definitely active
DELTA_MAG_TRANSITION_THRESHOLD = 0.2  # Between 0.2-0.5 = transition/minor movement

# Smoothing settings
MOVING_AVERAGE_WINDOW = 5  # Number of readings to average

# Database
DATABASE_URL = "sqlite:///./sedentary_tracker.db"

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
