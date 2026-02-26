
Para rodar: docker compose --env-file .env.grpc_tls up --build

Rodar gRPC com TLS:
docker compose --env-file .env.grpc_tls up --build

Rodar gRPC sem TLS:
docker compose --env-file .env.grpc_plain up --build

Rodar MQTT com TLS:
docker compose --env-file .env.mqtt_tls up --build

Rodar MQTT sem TLS:
docker compose --env-file .env.mqtt_plain up --build