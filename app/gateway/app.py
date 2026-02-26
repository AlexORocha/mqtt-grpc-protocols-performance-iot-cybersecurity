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
# gRPC CHANNEL CONFIG
# ============================

if MODE == "grpc":
    if USE_TLS:
        print("gRPC using TLS")

        with open("/certs/ca.crt", "rb") as f:
            trusted_certs = f.read()

        credentials = grpc.ssl_channel_credentials(trusted_certs)
        channel = grpc.secure_channel(GRPC_HOST, credentials)
    else:
        print("gRPC WITHOUT TLS")
        channel = grpc.insecure_channel(GRPC_HOST)

    stub = sensor_pb2_grpc.SensorServiceStub(channel)


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
        publish.single(
            MQTT_TOPIC,
            payload,
            hostname=MQTT_HOST,
            port=8883,
            tls={
                "ca_certs": "/certs/ca.crt"
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

    message = sensor_pb2.SensorData(
        temperature=data["temperature"],
        humidity=data["humidity"],
        current=data["current"],
        timestamp=data["timestamp"]
    )

    stub.SendData(message)


# ============================
# MAIN
# ============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)