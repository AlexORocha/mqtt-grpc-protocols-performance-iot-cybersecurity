import time
import json
import os

from flask import Flask, request, jsonify

# MQTT
import paho.mqtt.publish as publish

# gRPC
import grpc
import sensor_pb2
import sensor_pb2_grpc


app = Flask(__name__)

# ============================
# ENV CONFIG
# ============================
MODE = os.getenv("MODE", "mqtt").lower()
USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

MQTT_HOST = "mqtt"
MQTT_TOPIC = "sensor/data"

GRPC_HOST = "grpc_server:50051"

print(f"Gateway starting | MODE={MODE} | TLS={USE_TLS}")

# ============================
# gRPC CHANNEL CONFIG (LAZY)
# ============================

# Don't create channel at startup - create it on first use
grpc_channel = None
grpc_stub = None

def get_grpc_stub():
    """Get or create gRPC stub (lazy initialization)"""
    global grpc_channel, grpc_stub
    
    if grpc_stub is not None:
        return grpc_stub
    
    print(f"Initializing gRPC channel to {GRPC_HOST}...")
    
    if USE_TLS:
        print("gRPC using TLS")
        with open("/certs/ca.crt", "rb") as f:
            trusted_certs = f.read()
        credentials = grpc.ssl_channel_credentials(
            root_certificates=trusted_certs
        )
        grpc_channel = grpc.secure_channel(GRPC_HOST, credentials)
    else:
        print("gRPC WITHOUT TLS")
        grpc_channel = grpc.insecure_channel(
            GRPC_HOST,
            options=[
                ('grpc.enable_http_proxy', 0),
                ('grpc.dns_min_time_between_resolutions_ms', 10000),
            ]
        )
    
    grpc_stub = sensor_pb2_grpc.SensorServiceStub(grpc_channel)
    print("gRPC channel initialized successfully")
    return grpc_stub


# ============================
# ROUTE
# ============================

@app.route("/data", methods=["POST"])
def receive_data():
    data = request.json

    if not data:
        return jsonify({"error": "No JSON payload"}), 400

    start_time = time.time()

    try:
        if MODE == "mqtt":
            send_via_mqtt(data)
        elif MODE == "grpc":
            send_via_grpc(data)
        else:
            return jsonify({"error": "Invalid MODE"}), 500

    except Exception as e:
        print("Error sending:", e)
        return jsonify({"error": str(e)}), 500

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    print(f"[{MODE.upper()} | TLS={USE_TLS}] Latency: {latency_ms:.2f} ms")

    return jsonify({"status": "ok"})


# ============================
# MQTT SEND
# ============================

def send_via_mqtt(data):

    payload = json.dumps(data)

    if USE_TLS:
        import ssl
        publish.single(
            MQTT_TOPIC,
            payload,
            hostname=MQTT_HOST,
            port=8883,
            tls={
                "ca_certs": "/certs/ca.crt",
                "cert_reqs": ssl.CERT_REQUIRED,
                "tls_version": ssl.PROTOCOL_TLS
            }
        )
    else:
        publish.single(
            MQTT_TOPIC,
            payload,
            hostname=MQTT_HOST,
            port=1883
        )


# ============================
# gRPC SEND
# ============================

def send_via_grpc(data):
    """Send data via gRPC with retry logic"""
    max_retries = 3
    retry_delay = 0.5
    
    message = sensor_pb2.SensorData(
        temperature=data["temperature"],
        humidity=data["humidity"],
        current=data["current"],
        timestamp=data["timestamp"]
    )
    
    for attempt in range(max_retries):
        try:
            stub = get_grpc_stub()
            stub.SendData(message, timeout=5.0)
            return  # Success!
        except grpc.RpcError as e:
            if attempt < max_retries - 1:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    print(f"gRPC server unavailable (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay)
                    # Reset stub to force reconnection
                    global grpc_stub, grpc_channel
                    grpc_stub = None
                    if grpc_channel:
                        grpc_channel.close()
                        grpc_channel = None
                    continue
            raise  # Re-raise if last attempt or different error


# ============================
# MAIN
# ============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)