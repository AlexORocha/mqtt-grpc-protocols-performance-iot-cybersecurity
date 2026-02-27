# Testing with Variable Payload Sizes

Quick examples for testing with different payload configurations:

## Small Payloads (100-500 bytes)
Typical for simple sensor data (temperature, humidity, etc.)

```bash
# Edit .env file
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=500

# Run
docker compose up --build
```

## Medium Payloads (500-2KB)
For sensors with additional metadata or multiple readings

```bash
PAYLOAD_SIZE_MIN_BYTES=500
PAYLOAD_SIZE_MAX_BYTES=2000
```

## Large Payloads (2KB-10KB)
For rich sensor data, images, or audio samples

```bash
PAYLOAD_SIZE_MIN_BYTES=2000
PAYLOAD_SIZE_MAX_BYTES=10000
```

## Variable Load (50B-10KB)
Wide range to test protocol efficiency across sizes

```bash
PAYLOAD_SIZE_MIN_BYTES=50
PAYLOAD_SIZE_MAX_BYTES=10000
```

## Pre-configured Environments

```bash
# Standard size with network simulation
docker compose --env-file .env.mqtt_plain_simulated up --build

# MQTT with TLS and custom payload
PAYLOAD_SIZE_MIN_BYTES=10000 PAYLOAD_SIZE_MAX_BYTES=5000 \
  docker compose --env-file .env.mqtt_tls up --build
```

See [PAYLOAD_SIZE.md](PAYLOAD_SIZE.md) for detailed documentation.
