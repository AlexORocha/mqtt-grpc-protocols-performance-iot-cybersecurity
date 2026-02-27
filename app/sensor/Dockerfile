FROM python:3.11-slim

WORKDIR /app

COPY sensor/app.py .
COPY network_simulator.py .
COPY payload_generator.py .

RUN pip install requests

CMD ["python", "app.py"]