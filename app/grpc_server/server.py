import grpc
from concurrent import futures
import os
import time
import psycopg2
import sensor_pb2
import sensor_pb2_grpc

USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

DB_CONN = psycopg2.connect(
    host="postgres",
    database="iotlab",
    user="iot",
    password="iot"
)

class SensorService(sensor_pb2_grpc.SensorServiceServicer):

    def SendData(self, request, context):

        server_timestamp = time.time()
        latency_ms = (server_timestamp - request.timestamp) * 1000

        payload_size = request.ByteSize()

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
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(
        SensorService(), server
    )

    if USE_TLS:
        with open("/certs/server.key", "rb") as f:
            private_key = f.read()
        with open("/certs/server.crt", "rb") as f:
            certificate_chain = f.read()

        credentials = grpc.ssl_server_credentials(
            [(private_key, certificate_chain)]
        )

        server.add_secure_port("[::]:50051", credentials)
    else:
        server.add_insecure_port("[::]:50051")

    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()