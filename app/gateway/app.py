import time
import json
import os
import ssl

from flask import Flask, request, jsonify

# MQTT
import paho.mqtt.client as mqtt

# gRPC
import grpc
import sensor_pb2
import sensor_pb2_grpc

# Network Simulator
from network_simulator import get_simulator

app = Flask(__name__)

# Initialize network simulator
simulator = get_simulator()

# ============================
# ENV CONFIG
# ============================
MODE = os.getenv("MODE", "mqtt").lower()
USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"
ANALYZE_PAYLOAD_BEFORE = os.getenv("ANALYZE_PAYLOAD_BEFORE", "false").lower() == "true"

MQTT_HOST = "mqtt"
MQTT_TOPIC = "sensor/data"

GRPC_HOST = "grpc_server:50051"

print(f"Gateway starting | MODE={MODE} | TLS={USE_TLS} | ANALYZE_PAYLOAD_BEFORE={ANALYZE_PAYLOAD_BEFORE}")

# ============================
# MQTT CLIENT CONFIG (LAZY)
# ============================

mqtt_client = None
mqtt_connected = False

def mqtt_on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("MQTT client connected successfully")
    else:
        mqtt_connected = False
        print(f"MQTT connection failed with code {rc}")

def mqtt_on_disconnect(client, userdata, rc):
    """MQTT disconnection callback"""
    global mqtt_connected
    mqtt_connected = False
    if rc != 0:
        print(f"MQTT unexpected disconnect (rc={rc})")

def get_mqtt_client():
    """Get or create persistent MQTT client (lazy initialization)"""
    global mqtt_client, mqtt_connected
    
    # If client exists and is connected, return it
    if mqtt_client is not None and mqtt_connected:
        return mqtt_client
    
    # If client exists but not connected, try to reconnect
    if mqtt_client is not None and not mqtt_connected:
        try:
            print("Reconnecting MQTT client...")
            mqtt_client.reconnect()
            # Wait a bit for connection
            for _ in range(10):
                if mqtt_connected:
                    return mqtt_client
                time.sleep(0.1)
        except Exception as e:
            print(f"Reconnection failed: {e}, creating new client...")
            mqtt_client = None
    
    # Create new client
    print(f"Initializing MQTT client to {MQTT_HOST}...")
    mqtt_client = mqtt.Client(client_id="gateway", clean_session=True)
    mqtt_client.on_connect = mqtt_on_connect
    mqtt_client.on_disconnect = mqtt_on_disconnect
    
    if USE_TLS:
        print("MQTT using TLS")
        mqtt_client.tls_set(
            ca_certs="/certs/ca.crt",
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS
        )
        port = 8883
    else:
        print("MQTT without TLS")
        port = 1883
    
    # Connect with retry
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            mqtt_client.connect(MQTT_HOST, port, keepalive=60)
            mqtt_client.loop_start()  # Start network loop in background
            
            # Wait for connection
            for _ in range(20):  # Wait up to 2 seconds
                if mqtt_connected:
                    print("MQTT client initialized successfully")
                    return mqtt_client
                time.sleep(0.1)
            
            if not mqtt_connected and attempt < max_attempts - 1:
                print(f"Connection timeout (attempt {attempt + 1}/{max_attempts})")
                mqtt_client.loop_stop()
                continue
                
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"MQTT connection failed: {e} (attempt {attempt + 1}/{max_attempts})")
                time.sleep(0.5)
            else:
                raise Exception(f"Failed to connect to MQTT broker after {max_attempts} attempts")
    
    return mqtt_client

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
    # Simulate processing delay when receiving data
    simulator.add_processing_delay()
    
    data = request.json

    if not data:
        return jsonify({"error": "No JSON payload"}), 400

    # Calculate payload size BEFORE serialization (if enabled)
    if ANALYZE_PAYLOAD_BEFORE:
        payload_json = json.dumps(data)
        payload_size_before = len(payload_json.encode('utf-8'))
        data['payload_size_before'] = payload_size_before

    start_time = time.time()

    try:
        # Simulate network latency before forwarding
        simulator.add_network_latency()
        
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
    """Send data via MQTT using persistent connection"""
    payload = json.dumps(data)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_mqtt_client()
            
            # Publish with QoS 1 (at least once delivery)
            result = client.publish(MQTT_TOPIC, payload, qos=1)
            
            # Wait for publish to complete
            result.wait_for_publish(timeout=2.0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return  # Success!
            else:
                raise Exception(f"Publish failed with code {result.rc}")
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"MQTT publish failed: {e} (attempt {attempt + 1}/{max_retries}), retrying...")
                # Force reconnection on next attempt
                global mqtt_connected
                mqtt_connected = False
                time.sleep(0.3)
            else:
                raise


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
        timestamp=data["timestamp"],
        padding=data.get("padding", ""),  # Include padding if present
        payload_size_before=data.get("payload_size_before", 0)  # Size before serialization
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

def cleanup():
    """Cleanup connections on shutdown"""
    global mqtt_client, grpc_channel
    
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("MQTT client disconnected")
        except:
            pass
    
    if grpc_channel:
        try:
            grpc_channel.close()
            print("gRPC channel closed")
        except:
            pass

import atexit
atexit.register(cleanup)

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=8000)
    finally:
        cleanup()