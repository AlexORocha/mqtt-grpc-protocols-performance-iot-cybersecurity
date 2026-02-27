"""
Payload Generator - Creates variable-sized payloads for testing

This module generates sensor data with configurable payload sizes to test
protocol performance with different message sizes.
"""

import os
import random
import string
import json


class PayloadGenerator:
    """Generates sensor payloads with configurable sizes"""
    
    def __init__(self):
        self.min_size = int(os.getenv("PAYLOAD_SIZE_MIN_BYTES", "100"))
        self.max_size = int(os.getenv("PAYLOAD_SIZE_MAX_BYTES", "1000"))
        
        print(f"📦 Payload Generator initialized:")
        print(f"   Size range: {self.min_size}-{self.max_size} bytes")
    
    def generate_sensor_data(self, timestamp):
        """
        Generate sensor data with random payload size
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            dict: Sensor data with padding to reach target size
        """
        # Core sensor data
        data = {
            "temperature": round(random.uniform(20, 30), 2),
            "humidity": round(random.uniform(40, 60), 2),
            "current": round(random.uniform(1, 5), 2),
            "timestamp": timestamp
        }
        
        # Calculate current size
        current_size = len(json.dumps(data).encode('utf-8'))
        
        # Determine target size
        target_size = random.randint(self.min_size, self.max_size)
        
        # Add padding if needed
        if target_size > current_size:
            padding_size = target_size - current_size - 20  # Reserve space for JSON structure
            if padding_size > 0:
                # Generate random string for padding
                data["padding"] = ''.join(random.choices(string.ascii_letters + string.digits, k=padding_size))
        
        return data
    
    def get_payload_size(self, data):
        """Get the actual size of the payload in bytes"""
        return len(json.dumps(data).encode('utf-8'))


# Global singleton instance
_generator = None

def get_payload_generator():
    """Get the singleton payload generator instance"""
    global _generator
    if _generator is None:
        _generator = PayloadGenerator()
    return _generator
