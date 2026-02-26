import os
import json
import time
import ssl
import psycopg2
import paho.mqtt.client as mqtt

USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

MQTT_HOST = "mqtt"
MQTT_PORT = 8883 if USE_TLS else 1883
MQTT_TOPIC = "sensor/data"

print(f"MQTT Logger starting | TLS={USE_TLS}")

# ===============================
# DATABASE CONNECTION WITH RETRY
# ===============================

while True:
    try:
        DB_CONN = psycopg2.connect(
            host="postgres",
            database="iotlab",
            user="iot",
            password="iot"
        )
        DB_CONN.autocommit = True
        print("Connected to Postgres.")
        break
    except Exception as e:
        print("Waiting for Postgres...", e)
        time.sleep(2)

# ===============================
# CALLBACKS (COMPATÍVEL V1/V2)
# ===============================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(MQTT_TOPIC)
    else:
        print("Connection failed:", rc)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        server_timestamp = time.time()
        latency_ms = (server_timestamp - data["timestamp"]) * 1000
        payload_size = len(msg.payload)

        with DB_CONN.cursor() as cursor:
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
                "mqtt",
                USE_TLS,
                data.get("temperature"),
                data.get("humidity"),
                data.get("current"),
                data.get("timestamp"),
                server_timestamp,
                latency_ms,
                payload_size
            ))

    except Exception as e:
        print("Error processing message:", e)

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT. Reconnecting...")
    time.sleep(2)
    try:
        client.reconnect()
    except:
        pass

# ===============================
# MQTT CLIENT SETUP
# ===============================

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

if USE_TLS:
    client.tls_set(
        ca_certs="/certs/ca.crt",
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )
    client.tls_insecure_set(True)

client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

client.loop_forever()