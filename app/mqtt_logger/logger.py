import os
import json
import time
import ssl
import signal
import sys
import psycopg2
from psycopg2 import pool
import paho.mqtt.client as mqtt

# Add parent directory to path for imports
sys.path.insert(0, '/app')
from network_simulator import get_simulator

USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"

MQTT_HOST = "mqtt"
MQTT_PORT = 8883 if USE_TLS else 1883
MQTT_TOPIC = "sensor/data"

print(f"MQTT Logger starting | TLS={USE_TLS}")

# Initialize network simulator
simulator = get_simulator()

# ===============================
# DATABASE CONNECTION POOL
# ===============================

DB_POOL = None

def init_db_pool():
    """Initialize PostgreSQL connection pool with retry"""
    global DB_POOL
    max_retries = 30
    
    for i in range(max_retries):
        try:
            DB_POOL = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host="postgres",
                database="iotlab",
                user="iot",
                password="iot"
            )
            print("Connected to Postgres (connection pool created).")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"Waiting for Postgres... (attempt {i + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"Failed to connect to Postgres after {max_retries} attempts")
                raise
    return False

def get_db_connection():
    """Get a connection from the pool with auto-retry"""
    global DB_POOL
    try:
        if DB_POOL is None:
            init_db_pool()
        return DB_POOL.getconn()
    except Exception as e:
        print(f"Error getting DB connection: {e}")
        # Try to reinitialize pool
        DB_POOL = None
        init_db_pool()
        return DB_POOL.getconn()

def return_db_connection(conn):
    """Return connection to the pool"""
    if DB_POOL and conn:
        DB_POOL.putconn(conn)

# Initialize database pool
init_db_pool()

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
    conn = None
    try:
        # Simulate processing delay when receiving message
        simulator.add_processing_delay()
        
        data = json.loads(msg.payload.decode())

        server_timestamp = time.time()
        latency_ms = (server_timestamp - data["timestamp"]) * 1000
        payload_size = len(msg.payload)

        # Simulate network latency before storing to DB
        simulator.add_network_latency()
        
        # Get connection from pool
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        
        conn.commit()
        cursor.close()
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        # Return connection to pool
        if conn:
            return_db_connection(conn)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection from MQTT (rc={rc}). Reconnecting...")
        reconnect_count = 0
        max_reconnect_attempts = 10
        
        while reconnect_count < max_reconnect_attempts:
            try:
                time.sleep(min(2 ** reconnect_count, 60))  # Exponential backoff (max 60s)
                print(f"Reconnection attempt {reconnect_count + 1}/{max_reconnect_attempts}...")
                client.reconnect()
                print("Reconnected successfully!")
                break
            except Exception as e:
                reconnect_count += 1
                print(f"Reconnection failed: {e}")
                if reconnect_count >= max_reconnect_attempts:
                    print("Max reconnection attempts reached. Exiting...")
                    raise
    else:
        print("Disconnected from MQTT broker (clean disconnect).")

# ===============================
# MQTT CLIENT SETUP
# ===============================

# Create MQTT client with clean session
client = mqtt.Client(client_id="", clean_session=True)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

if USE_TLS:
    client.tls_set(
        ca_certs="/certs/ca.crt",
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS
    )

# Enable automatic reconnection
client.reconnect_delay_set(min_delay=1, max_delay=120)

# ===============================
# GRACEFUL SHUTDOWN
# ===============================

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\nShutdown signal received. Cleaning up...")
    
    # Disconnect MQTT
    try:
        client.disconnect()
        print("MQTT client disconnected.")
    except:
        pass
    
    # Close DB pool
    try:
        if DB_POOL:
            DB_POOL.closeall()
            print("Database connections closed.")
    except:
        pass
    
    print("Shutdown complete.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ===============================
# CONNECT AND START
# ===============================

# Connect with retry
max_connection_attempts = 10
for attempt in range(max_connection_attempts):
    try:
        print(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT} (attempt {attempt + 1}/{max_connection_attempts})...")
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        break
    except Exception as e:
        print(f"Connection failed: {e}")
        if attempt < max_connection_attempts - 1:
            time.sleep(2)
        else:
            print("Max connection attempts reached. Exiting...")
            raise

print("Starting MQTT loop...")
client.loop_forever()