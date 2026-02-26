#!/bin/bash

set -e

SCENARIOS=(
  ".env.mqtt_plain"
  ".env.mqtt_tls"
  ".env.grpc_plain"
  ".env.grpc_tls"
)

TARGET_ROWS=1000
RESULTS_DIR="results"

mkdir -p $RESULTS_DIR

echo "========================================"
echo "STARTING FULL EXPERIMENT SUITE"
echo "========================================"

for ENV_FILE in "${SCENARIOS[@]}"
do
  SCENARIO_NAME=$(basename $ENV_FILE .env)
  echo ""
  echo "----------------------------------------"
  echo "Running scenario: $SCENARIO_NAME"
  echo "----------------------------------------"

  # Limpeza total
  docker compose down -v || true

  # Limpa capturas antigas
  rm -f captures/capture.pcap || true

  # Sobe ambiente
  docker compose --env-file $ENV_FILE up --build -d

  echo "Waiting for containers to stabilize..."
  sleep 10

  echo "Collecting data until $TARGET_ROWS rows..."

  while true
  do
    COUNT=$(docker exec logger_db psql -U iot -d iotlab -t -c "SELECT COUNT(*) FROM message_logs;" | xargs)

    echo "Current rows: $COUNT"

    if [ "$COUNT" -ge "$TARGET_ROWS" ]; then
      break
    fi

    sleep 2
  done

  echo "Target reached. Collecting metrics..."

  # Export database results
  docker exec logger_db psql -U iot -d iotlab -c "\copy message_logs to '/tmp/${SCENARIO_NAME}.csv' csv header"
  docker cp logger_db:/tmp/${SCENARIO_NAME}.csv $RESULTS_DIR/${SCENARIO_NAME}.csv

  # Coleta stats dos containers
  docker stats --no-stream --format \
  "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" \
  > $RESULTS_DIR/${SCENARIO_NAME}_stats.csv

  # Salva PCAP se existir
  if [ -f captures/capture.pcap ]; then
    mv captures/capture.pcap $RESULTS_DIR/${SCENARIO_NAME}.pcap
  fi

  echo "Stopping scenario..."

  docker compose down -v

  echo "Scenario $SCENARIO_NAME completed."
done

echo ""
echo "========================================"
echo "ALL EXPERIMENTS COMPLETED"
echo "Results saved in /results"
echo "========================================"