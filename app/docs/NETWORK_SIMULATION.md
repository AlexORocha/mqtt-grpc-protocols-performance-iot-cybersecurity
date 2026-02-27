# Network Simulation for Distributed Systems

This feature adds artificial latency and jitter to simulate realistic distributed IoT environments where:
- Sensors are on edge devices with varying processing power
- Network connections have latency and packet delays
- Gateways and servers process data with realistic delays

## Configuration

Add these variables to your `.env` file:

```bash
# Enable/disable simulation
ENABLE_NETWORK_SIMULATION=true

# Network latency range (milliseconds)
NETWORK_LATENCY_MIN_MS=5
NETWORK_LATENCY_MAX_MS=50

# Hardware processing delay range (milliseconds)
PROCESSING_DELAY_MIN_MS=1
PROCESSING_DELAY_MAX_MS=10
```

## How It Works

### Network Latency
Simulates network transmission delays between components:
- **Sensor → Gateway**: Network delay before HTTP request
- **Gateway → MQTT/gRPC**: Network delay before publishing/calling
- **Logger/Server → Database**: Network delay before storing

### Processing Delay
Simulates hardware processing time:
- **Sensor**: Time to read sensor values
- **Gateway**: Time to process and forward data
- **Logger/Server**: Time to process incoming messages

### Applied Locations

1. **Sensor** ([sensor/app.py](sensor/app.py))
   - Processing delay: Simulates sensor reading time
   - Network latency: Before sending HTTP request

2. **Gateway** ([gateway/app.py](gateway/app.py))
   - Processing delay: When receiving data from sensor
   - Network latency: Before forwarding to MQTT/gRPC

3. **MQTT Logger** ([mqtt_logger/logger.py](mqtt_logger/logger.py))
   - Processing delay: When processing MQTT message
   - Network latency: Before storing to database

4. **gRPC Server** ([grpc_server/server.py](grpc_server/server.py))
   - Processing delay: When processing gRPC request
   - Network latency: Before storing to database

## Example Configurations

### Realistic IoT Network (Default)
Simulates typical IoT deployments with WiFi/4G connections:
```bash
ENABLE_NETWORK_SIMULATION=true
NETWORK_LATENCY_MIN_MS=5
NETWORK_LATENCY_MAX_MS=50
PROCESSING_DELAY_MIN_MS=1
PROCESSING_DELAY_MAX_MS=10
```

### Poor Network Conditions
Simulates congested or long-distance networks:
```bash
ENABLE_NETWORK_SIMULATION=true
NETWORK_LATENCY_MIN_MS=50
NETWORK_LATENCY_MAX_MS=200
PROCESSING_DELAY_MIN_MS=5
PROCESSING_DELAY_MAX_MS=30
```

### Low-Power Edge Devices
Simulates constrained hardware (MCUs, low-power CPUs):
```bash
ENABLE_NETWORK_SIMULATION=true
NETWORK_LATENCY_MIN_MS=10
NETWORK_LATENCY_MAX_MS=80
PROCESSING_DELAY_MIN_MS=10
PROCESSING_DELAY_MAX_MS=50
```

### Ideal Conditions (No Simulation)
For baseline performance measurements:
```bash
ENABLE_NETWORK_SIMULATION=true
```

## Testing

### Run with simulation enabled:
```bash
# Use pre-configured simulated environment
docker compose --env-file .env.mqtt_plain_simulated up --build

# Or modify any existing .env file:
docker compose --env-file .env.mqtt_plain up --build
```

### Compare results:
```bash
# Without simulation
ENABLE_NETWORK_SIMULATION=true docker compose up

# With simulation  
ENABLE_NETWORK_SIMULATION=true docker compose up

# Check latency differences in logs
```

## Impact on Measurements

The simulator adds realistic delays that will be reflected in your latency measurements:

- **Without simulation**: Measures only protocol overhead and local processing
- **With simulation**: Measures protocol overhead + simulated network/hardware delays

This provides more realistic performance data for real-world deployments.

## Implementation Details

The `NetworkSimulator` class ([network_simulator.py](network_simulator.py)) uses:
- **Uniform distribution**: Random delays within min-max range
- **Non-blocking**: Uses `time.sleep()` for simplicity
- **Per-operation**: Each network/processing operation adds independent delay
- **Singleton pattern**: Single instance shared across the application

## Notes

- Delays are added to **both successful and failed operations**
- Simulation affects **end-to-end latency** visible in database measurements
- Does **not** simulate packet loss or connection errors (only delays)
- Safe to enable in development/testing (disabled by default in production)
