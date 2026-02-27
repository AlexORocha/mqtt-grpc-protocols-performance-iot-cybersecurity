FROM python:3.11-slim

WORKDIR /app

COPY mqtt_logger/logger.py .
COPY network_simulator.py .

RUN pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    psycopg2-binary

CMD ["python", "logger.py"]