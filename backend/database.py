"""
Database setup and models for SQLite storage
"""

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

from config import DATABASE_URL

# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class SensorReadingDB(Base):
    """Database model for sensor readings"""
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, index=True)
    pir = Column(Integer)  # 0 or 1
    delta_mag = Column(Float)
    delta_mag_smoothed = Column(Float)
    inactive_seconds = Column(Integer)
    alerted = Column(Integer)  # 0 or 1
    activity_state = Column(String)  # 'active', 'inactive', 'transition'
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertEventDB(Base):
    """Database model for sedentary alert events"""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, index=True)
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize the database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Run this file directly to initialize the database
    init_db()
