import time
import requests
import random
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, '/app')
from network_simulator import get_simulator
from payload_generator import get_payload_generator

# Initialize network simulator and payload generator
simulator = get_simulator()
payload_gen = get_payload_generator()

while True:
    # Simulate sensor reading time
    simulator.add_processing_delay()
    
    # Generate sensor data with variable payload size
    payload = payload_gen.generate_sensor_data(time.time())

    # Simulate network latency before sending
    simulator.add_network_latency()
    
    requests.post("http://gateway:8000/data", json=payload)
    
    # Show actual payload size
    actual_size = payload_gen.get_payload_size(payload)
    print(f"Data sent: temp={payload['temperature']}, hum={payload['humidity']}, size={actual_size}B")

    time.sleep(0.01)