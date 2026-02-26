FROM python:3.11-slim

WORKDIR /app

COPY logger.py .

RUN pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    psycopg2-binary

CMD ["python", "logger.py"]