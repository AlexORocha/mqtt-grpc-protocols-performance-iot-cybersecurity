FROM python:3.11-slim

WORKDIR /app

COPY gateway /app
COPY proto /app/proto
COPY network_simulator.py /app/

RUN pip install flask paho-mqtt grpcio grpcio-tools

RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=. \
    --grpc_python_out=. \
    proto/sensor.proto

CMD ["python", "app.py"]