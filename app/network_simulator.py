"""
Network Simulator - Adds artificial latency and jitter to simulate distributed systems

This module simulates realistic network conditions and hardware processing delays
to better represent IoT devices, gateways, and servers running on different hardware
and connected through real networks.
"""

import os
import time
import random


class NetworkSimulator:
    """Simulates network latency and processing delays"""
    
    def __init__(self):
        self.enabled = os.getenv("ENABLE_NETWORK_SIMULATION", "false").lower() == "true"
        
        # Network latency (in seconds)
        self.network_latency_min = float(os.getenv("NETWORK_LATENCY_MIN_MS", "5")) / 1000.0
        self.network_latency_max = float(os.getenv("NETWORK_LATENCY_MAX_MS", "50")) / 1000.0
        
        # Processing delay (in seconds)
        self.processing_delay_min = float(os.getenv("PROCESSING_DELAY_MIN_MS", "1")) / 1000.0
        self.processing_delay_max = float(os.getenv("PROCESSING_DELAY_MAX_MS", "10")) / 1000.0
        
        if self.enabled:
            print(f"🌐 Network Simulation ENABLED:")
            print(f"   Network latency: {self.network_latency_min*1000:.1f}-{self.network_latency_max*1000:.1f} ms")
            print(f"   Processing delay: {self.processing_delay_min*1000:.1f}-{self.processing_delay_max*1000:.1f} ms")
    
    def add_network_latency(self):
        """Simulate network transmission delay with jitter"""
        if not self.enabled:
            return
        
        # Random delay between min and max (uniform distribution)
        delay = random.uniform(self.network_latency_min, self.network_latency_max)
        time.sleep(delay)
    
    def add_processing_delay(self):
        """Simulate hardware processing time"""
        if not self.enabled:
            return
        
        # Random delay between min and max (uniform distribution)
        delay = random.uniform(self.processing_delay_min, self.processing_delay_max)
        time.sleep(delay)
    
    def add_full_delay(self):
        """Add both network and processing delays"""
        if not self.enabled:
            return
        
        # Network latency + processing delay
        total_delay = (
            random.uniform(self.network_latency_min, self.network_latency_max) +
            random.uniform(self.processing_delay_min, self.processing_delay_max)
        )
        time.sleep(total_delay)


# Global singleton instance
_simulator = None

def get_simulator():
    """Get the singleton network simulator instance"""
    global _simulator
    if _simulator is None:
        _simulator = NetworkSimulator()
    return _simulator
