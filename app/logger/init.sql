CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    protocol VARCHAR(10) NOT NULL,
    use_tls BOOLEAN NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    current DOUBLE PRECISION,
    client_timestamp DOUBLE PRECISION,
    server_timestamp DOUBLE PRECISION,
    latency_ms DOUBLE PRECISION,
    payload_size_bytes INTEGER,
    payload_size_before_bytes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);