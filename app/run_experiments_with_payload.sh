#!/bin/bash

set -e

SCENARIOS=(
  ".env.mqtt_plain"
  ".env.mqtt_tls"
  ".env.grpc_plain"
  ".env.grpc_tls"
)

TARGET_ROWS=10000
RESULTS_DIR="results"

mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "STARTING PAYLOAD ANALYSIS EXPERIMENTS"
echo "ANALYZE_PAYLOAD_BEFORE=true (enabled)"
echo "========================================"

# Start PostgreSQL once (it will persist across all scenarios)
echo "Starting PostgreSQL database..."
docker compose up postgres -d
sleep 5

for ENV_FILE in "${SCENARIOS[@]}"
do
  # Remove prefix ".env."
  CLEAN_NAME=${ENV_FILE/.env./}

  # Nome final padronizado
  SCENARIO_NAME="results_${CLEAN_NAME}_payload"

  echo ""
  echo "----------------------------------------"
  echo "Running scenario: $SCENARIO_NAME"
  echo "----------------------------------------"

  # Stop only application containers (keep postgres running)
  docker compose stop sensor gateway mqtt_logger grpc_server mqtt sniffer || true
  docker compose rm -f sensor gateway mqtt_logger grpc_server mqtt sniffer || true

  # Remove captura antiga
  rm -f captures/capture.pcap || true

  # Create temporary env file with ANALYZE_PAYLOAD_BEFORE=true
  TEMP_ENV_FILE=".env.temp_with_payload"
  cp "$ENV_FILE" "$TEMP_ENV_FILE"
  
  # Force ANALYZE_PAYLOAD_BEFORE to true
  # Remove existing line if present, then append
  grep -v "ANALYZE_PAYLOAD_BEFORE" "$TEMP_ENV_FILE" > "${TEMP_ENV_FILE}.tmp" || true
  mv "${TEMP_ENV_FILE}.tmp" "$TEMP_ENV_FILE"
  echo "" >> "$TEMP_ENV_FILE"
  echo "# Enable payload size analysis (added by run_experiments_with_payload.sh)" >> "$TEMP_ENV_FILE"
  echo "ANALYZE_PAYLOAD_BEFORE=true" >> "$TEMP_ENV_FILE"
  
  echo "Using environment file with ANALYZE_PAYLOAD_BEFORE=true"
  
  # Sobe ambiente com arquivo temporário (force rebuild to pick up changes)
  docker compose --env-file "$TEMP_ENV_FILE" up --build -d

  echo "Waiting for containers to stabilize..."
  sleep 10

  # Get initial count before starting this scenario
  INITIAL_COUNT=$(docker exec logger_db psql -U iot -d iotlab -t -c "SELECT COUNT(*) FROM message_logs;" | xargs)
  TARGET_TOTAL=$((INITIAL_COUNT + TARGET_ROWS))

  echo "Initial rows in database: $INITIAL_COUNT"
  echo "Collecting data until $TARGET_TOTAL rows (adding $TARGET_ROWS new rows)..."

  while true
  do
    COUNT=$(docker exec logger_db psql -U iot -d iotlab -t -c "SELECT COUNT(*) FROM message_logs;" | xargs)
    NEW_ROWS=$((COUNT - INITIAL_COUNT))

    echo "Total rows: $COUNT | New rows from this scenario: $NEW_ROWS / $TARGET_ROWS"

    if [ "$COUNT" -ge "$TARGET_TOTAL" ]; then
      break
    fi

    sleep 2
  done

  echo "Target reached. Collecting metrics..."

  # Exporta dados do banco
  docker exec logger_db psql -U iot -d iotlab \
    -c "\copy message_logs to '/tmp/${SCENARIO_NAME}.csv' csv header"

  docker cp logger_db:/tmp/${SCENARIO_NAME}.csv \
    "$RESULTS_DIR/${SCENARIO_NAME}.csv"

  # Coleta stats dos containers
  docker stats --no-stream --format \
  "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" \
  > "$RESULTS_DIR/${SCENARIO_NAME}_stats.csv"

  # Salva PCAP
  if [ -f captures/capture.pcap ]; then
    mv captures/capture.pcap "$RESULTS_DIR/${SCENARIO_NAME}.pcap"
  fi

  # Remove temporary env file
  rm -f "$TEMP_ENV_FILE"

  echo "Stopping application containers..."
  docker compose stop sensor gateway mqtt_logger grpc_server mqtt sniffer || true

  echo "Scenario $SCENARIO_NAME completed."
done

# Stop all application containers but keep postgres running
echo ""
echo "Stopping application containers (keeping postgres running)..."
docker compose stop sensor gateway mqtt_logger grpc_server mqtt sniffer || true
docker compose rm -f sensor gateway mqtt_logger grpc_server mqtt sniffer || true

echo ""
echo "========================================"
echo "ALL PAYLOAD EXPERIMENTS COMPLETED"
echo "Results saved in /$RESULTS_DIR"
echo ""
echo "📊 PostgreSQL is still running with ALL data"
echo "   Run 'python analyze_payload_v2.py' to analyze"
echo ""
echo "To stop postgres: docker compose stop postgres"
echo "========================================"
