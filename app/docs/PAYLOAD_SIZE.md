# Payload Size Configuration

This feature allows you to test protocol performance with different message (payload) sizes.

## Configuration

Add these variables to your `.env` file:

```bash
# Payload size range in bytes
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=1000
```

## How It Works

The `PayloadGenerator` class ([payload_generator.py](payload_generator.py)) generates sensor data with variable sizes:

1. **Core Data**: Basic sensor readings (temperature, humidity, current, timestamp)
2. **Padding**: Random alphanumeric string added to reach target size
3. **Random Size**: Each message has a random size between min and max

### Example Payloads

**Small payload (~100 bytes)**:
```json
{
  "temperature": 25.34,
  "humidity": 45.67,
  "current": 3.21,
  "timestamp": 1772153556.123,
  "padding": "a7f3k9x2..."
}
```

**Large payload (~1000 bytes)**:
```json
{
  "temperature": 27.89,
  "humidity": 52.11,
  "current": 2.45,
  "timestamp": 1772153557.456,
  "padding": "xK8pL3mN9qR2vT5wY7zA4bD6fG8hJ0kM1nP3rS5uX7yB9cE1gI3jL5oQ7sU9wZ1aC3eH5iK7mO9pR1tV3xA5zD7fJ9lN1qT3vY5..."
}
```

## Stored Information

The actual payload size (in bytes) is calculated and stored in the database:
- **Column**: `payload_size_bytes` (INTEGER)
- **Calculation**: 
  - MQTT: `len(msg.payload)` - actual wire size
  - gRPC: `request.ByteSize()` - protobuf serialized size

This allows you to analyze protocol overhead and efficiency with different message sizes.

## Use Cases

### Test Protocol Efficiency
Compare how MQTT and gRPC handle different payload sizes:
```bash
# Small messages (100-500 bytes)
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=500

# Medium messages (500-2000 bytes)
PAYLOAD_SIZE_MIN_BYTES=500
PAYLOAD_SIZE_MAX_BYTES=2000

# Large messages (2000-10000 bytes)
PAYLOAD_SIZE_MIN_BYTES=2000
PAYLOAD_SIZE_MAX_BYTES=10000
```

### Bandwidth Testing
Simulate different IoT scenarios:
```bash
# Minimal sensor data (light sensors, buttons)
PAYLOAD_SIZE_MIN_BYTES=50
PAYLOAD_SIZE_MAX_BYTES=200

# Standard sensor data (temp, humidity, etc)
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=1000

# Rich sensor data (images, audio samples)
PAYLOAD_SIZE_MIN_BYTES=5000
PAYLOAD_SIZE_MAX_BYTES=50000
```

## Analysis Queries

After running experiments, analyze payload performance:

```sql
-- Average payload size by protocol
SELECT protocol, use_tls, 
       AVG(payload_size_bytes) as avg_size,
       AVG(latency_ms) as avg_latency
FROM message_logs
GROUP BY protocol, use_tls;

-- Latency vs payload size correlation
SELECT 
    CASE 
        WHEN payload_size_bytes < 500 THEN 'small'
        WHEN payload_size_bytes < 2000 THEN 'medium'
        ELSE 'large'
    END as size_category,
    protocol,
    AVG(latency_ms) as avg_latency,
    COUNT(*) as message_count
FROM message_logs
GROUP BY size_category, protocol
ORDER BY size_category, protocol;

-- Protocol overhead calculation
SELECT protocol, use_tls,
       AVG(payload_size_bytes) as avg_payload,
       AVG(latency_ms) as avg_latency,
       AVG(latency_ms) / AVG(payload_size_bytes) as latency_per_byte
FROM message_logs
GROUP BY protocol, use_tls;
```

## Example Configurations

### Baseline (small payloads)
```bash
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=500
```

### Stress Test (large payloads)
```bash
PAYLOAD_SIZE_MIN_BYTES=5000
PAYLOAD_SIZE_MAX_BYTES=20000
```

### Variable Load (wide range)
```bash
PAYLOAD_SIZE_MIN_BYTES=50
PAYLOAD_SIZE_MAX_BYTES=10000
```

## Implementation Details

- **Encoding**: UTF-8 JSON format
- **Padding**: Random alphanumeric characters (a-z, A-Z, 0-9)
- **Distribution**: Uniform random between min and max
- **Overhead**: ~20 bytes reserved for JSON structure

## Notes

- The `padding` field is automatically added/adjusted to reach target size
- Actual payload size may vary slightly due to JSON encoding
- Size is measured after JSON serialization (wire format)
- Works with both MQTT (JSON) and gRPC (converted to protobuf)
