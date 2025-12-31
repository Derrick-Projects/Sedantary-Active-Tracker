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

# Database - PostgreSQL
# Format: postgresql://username:password@host:port/database
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "root"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "sedentary_tracker"

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
