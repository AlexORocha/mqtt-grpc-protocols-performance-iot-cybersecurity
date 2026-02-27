import time
import requests
import random


while True:
    payload = {
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 60), 2),
        "current": round(random.uniform(1, 5), 2),
        "timestamp": time.time()
    }

    requests.post("http://gateway:8000/data", json=payload)
    print("Data sent:", payload)

    time.sleep(0.01)