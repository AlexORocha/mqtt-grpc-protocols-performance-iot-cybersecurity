FROM python:3.11-slim

WORKDIR /app

COPY grpc_server /app
COPY proto /app/proto

RUN pip install grpcio grpcio-tools psycopg2-binary

RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=. \
    --grpc_python_out=. \
    proto/sensor.proto

CMD ["python", "server.py"]