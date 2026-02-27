import grpc
from concurrent import futures
import os
import time
import psycopg2
import sensor_pb2
import sensor_pb2_grpc
from network_simulator import get_simulator

USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

# Initialize network simulator
simulator = get_simulator()

# Wait for PostgreSQL to be ready
print("Waiting for PostgreSQL...")
max_retries = 30
for i in range(max_retries):
    try:
        DB_CONN = psycopg2.connect(
            host="postgres",
            database="iotlab",
            user="iot",
            password="iot"
        )
        print("Connected to PostgreSQL successfully")
        break
    except psycopg2.OperationalError as e:
        if i < max_retries - 1:
            print(f"PostgreSQL not ready yet (attempt {i + 1}/{max_retries}), waiting...")
            time.sleep(1)
        else:
            print(f"Failed to connect to PostgreSQL after {max_retries} attempts")
            raise

class SensorService(sensor_pb2_grpc.SensorServiceServicer):

    def SendData(self, request, context):
        # Simulate processing delay when receiving request
        simulator.add_processing_delay()
        
        server_timestamp = time.time()
        latency_ms = (server_timestamp - request.timestamp) * 1000

        payload_size = request.ByteSize()

        # Simulate network latency before storing to DB
        simulator.add_network_latency()
        
        cursor = DB_CONN.cursor()
        cursor.execute("""
            INSERT INTO message_logs (
                protocol,
                use_tls,
                temperature,
                humidity,
                current,
                client_timestamp,
                server_timestamp,
                latency_ms,
                payload_size_bytes
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            "grpc",
            USE_TLS,
            request.temperature,
            request.humidity,
            request.current,
            request.timestamp,
            server_timestamp,
            latency_ms,
            payload_size
        ))

        DB_CONN.commit()
        cursor.close()

        return sensor_pb2.Ack(status="ok")


def serve():
    print(f"Starting gRPC server | TLS={USE_TLS}")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(
        SensorService(), server
    )

    if USE_TLS:
        print("Configuring TLS...")
        with open("/certs/server.key", "rb") as f:
            private_key = f.read()
        with open("/certs/server.crt", "rb") as f:
            certificate_chain = f.read()

        credentials = grpc.ssl_server_credentials(
            [(private_key, certificate_chain)]
        )

        server.add_secure_port("[::]:50051", credentials)
        print("gRPC server listening on port 50051 with TLS")
    else:
        server.add_insecure_port("[::]:50051")
        print("gRPC server listening on port 50051 without TLS")

    server.start()
    print("gRPC server started successfully - ready to accept connections")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()