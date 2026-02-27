
Para rodar: docker compose --env-file .env.grpc_tls up --build

## Configurações Disponíveis

### Protocolos e TLS
Rodar gRPC com TLS:
docker compose --env-file .env.grpc_tls up --build

Rodar gRPC sem TLS:
docker compose --env-file .env.grpc_plain up --build

Rodar MQTT com TLS:
docker compose --env-file .env.mqtt_tls up --build

Rodar MQTT sem TLS:
docker compose --env-file .env.mqtt_plain up --build

### Simulação de Rede e Tamanhos de Payload

Rodar com simulação de rede realista:
docker compose --env-file .env.mqtt_plain_simulated up --build

Testar com payloads pequenos (100-500 bytes):
docker compose --env-file .env.small_payload up --build

Testar com payloads grandes (5KB-20KB):
docker compose --env-file .env.large_payload up --build

## Recursos Avançados

- **Simulação de Rede**: Adiciona latência artificial para simular ambientes distribuídos
  - Ver: [NETWORK_SIMULATION.md](app/NETWORK_SIMULATION.md)

- **Tamanhos Variáveis de Payload**: Testa protocolos com diferentes tamanhos de mensagem
  - Ver: [PAYLOAD_SIZE.md](app/PAYLOAD_SIZE.md)
  - Exemplos: [PAYLOAD_EXAMPLES.md](app/PAYLOAD_EXAMPLES.md)

- **Certificados TLS**: Geração automática de certificados para comunicação segura
  - Ver: [certs/README.md](app/certs/README.md)

## Variáveis de Ambiente

Principais configurações disponíveis nos arquivos `.env`:

```bash
# Protocolo e Segurança
MODE=mqtt|grpc
USE_TLS=true|false

# Simulação de Rede
ENABLE_NETWORK_SIMULATION=true|false
NETWORK_LATENCY_MIN_MS=5
NETWORK_LATENCY_MAX_MS=50
PROCESSING_DELAY_MIN_MS=1
PROCESSING_DELAY_MAX_MS=10

# Tamanho do Payload
PAYLOAD_SIZE_MIN_BYTES=100
PAYLOAD_SIZE_MAX_BYTES=1000
```