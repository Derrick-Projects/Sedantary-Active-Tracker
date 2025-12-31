"""
Serial port reader for live Arduino data
"""

import serial
import threading
import time
from datetime import datetime
from typing import Optional, Callable, List
from queue import Queue

from config import SERIAL_PORT, BAUD_RATE
from models import SensorReading


class SerialReader:
    """
    Reads CSV data from Arduino via serial port.
    Runs in a separate thread to avoid blocking the main application.
    """

    def __init__(self, port: str = SERIAL_PORT, baud_rate: int = BAUD_RATE):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection: Optional[serial.Serial] = None
        self.is_running = False
        self.read_thread: Optional[threading.Thread] = None
        
        # Queue for thread-safe data transfer
        self.data_queue: Queue = Queue()
        
        # Callback for real-time processing
        self.on_reading_callback: Optional[Callable[[SensorReading], None]] = None
        
        # Buffer for recent readings
        self.recent_readings: List[SensorReading] = []
        self.max_recent_readings = 100

    def connect(self) -> bool:
        """
        Establish connection to the serial port.
        Returns True if successful, False otherwise.
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1
            )
            print(f"Connected to {self.port} at {self.baud_rate} baud")
            
            # Wait for Arduino to reset after connection
            time.sleep(2)
            
            # Clear any startup messages
            self.serial_connection.flushInput()
            
            return True
            
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False

    def disconnect(self):
        """Close the serial connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"Disconnected from {self.port}")

    def parse_csv_line(self, line: str) -> Optional[SensorReading]:
        """
        Parse a CSV line from Arduino.
        Expected format: timestamp,pir,deltaMag,inactiveSeconds,alerted
        Example: 2025-12-31 14:30:15,1,0.234,5,0
        """
        try:
            # Skip header lines or non-data lines
            if line.startswith("Sedentary") or line.startswith("CSV") or line.startswith("-"):
                return None
            
            # Skip alert messages
            if "SEDENTARY ALERT" in line or "inactive for" in line:
                return None
            
            parts = line.strip().split(",")
            
            if len(parts) != 5:
                return None
            
            # Parse timestamp
            timestamp = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
            
            # Parse sensor values
            pir = int(parts[1])
            delta_mag = float(parts[2])
            inactive_seconds = int(parts[3])
            alerted = int(parts[4])
            
            return SensorReading(
                timestamp=timestamp,
                pir=pir,
                delta_mag=delta_mag,
                inactive_seconds=inactive_seconds,
                alerted=alerted
            )
            
        except (ValueError, IndexError) as e:
            # Invalid line format - skip it
            return None

    def _read_loop(self):
        """Main reading loop - runs in separate thread"""
        print("Serial reading started...")
        
        while self.is_running:
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    # Read line from serial
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore')
                    
                    # Parse the CSV data
                    reading = self.parse_csv_line(line)
                    
                    if reading:
                        # Add to queue for main thread
                        self.data_queue.put(reading)
                        
                        # Store in recent readings buffer
                        self.recent_readings.append(reading)
                        if len(self.recent_readings) > self.max_recent_readings:
                            self.recent_readings.pop(0)
                        
                        # Call callback if registered
                        if self.on_reading_callback:
                            self.on_reading_callback(reading)
                
                else:
                    # Small delay to prevent busy waiting
                    time.sleep(0.05)
                    
            except Exception as e:
                print(f"Error reading from serial: {e}")
                time.sleep(0.5)
        
        print("Serial reading stopped.")

    def start_reading(self):
        """Start the background reading thread"""
        if self.is_running:
            print("Already reading")
            return
        
        if not self.serial_connection or not self.serial_connection.is_open:
            if not self.connect():
                print("Failed to connect. Cannot start reading.")
                return
        
        self.is_running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        print("Background reading thread started")

    def stop_reading(self):
        """Stop the background reading thread"""
        self.is_running = False
        
        if self.read_thread:
            self.read_thread.join(timeout=2)
        
        self.disconnect()

    def get_pending_readings(self) -> List[SensorReading]:
        """Get all pending readings from the queue"""
        readings = []
        while not self.data_queue.empty():
            readings.append(self.data_queue.get())
        return readings

    def get_recent_readings(self, count: int = 50) -> List[SensorReading]:
        """Get the most recent readings"""
        return self.recent_readings[-count:]

    def set_callback(self, callback: Callable[[SensorReading], None]):
        """Set callback function to be called for each new reading"""
        self.on_reading_callback = callback


# Singleton instance for global access
_serial_reader: Optional[SerialReader] = None


def get_serial_reader() -> SerialReader:
    """Get or create the global serial reader instance"""
    global _serial_reader
    if _serial_reader is None:
        _serial_reader = SerialReader()
    return _serial_reader


if __name__ == "__main__":
    # Test the serial reader
    reader = SerialReader()
    
    def on_reading(reading: SensorReading):
        print(f"Received: {reading.timestamp} | PIR: {reading.pir} | "
              f"DeltaMag: {reading.delta_mag:.3f} | Inactive: {reading.inactive_seconds}s")
    
    reader.set_callback(on_reading)
    
    if reader.connect():
        reader.start_reading()
        
        try:
            print("Reading from serial port. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            reader.stop_reading()
