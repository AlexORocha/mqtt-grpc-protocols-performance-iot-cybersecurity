# TLS Certificates

Este diretório contém os certificados TLS para comunicação segura com o broker MQTT.

## Arquivos

- **ca.crt** - Certificado da Autoridade Certificadora (CA) self-signed
- **ca.key** - Chave privada da CA
- **server.crt** - Certificado do servidor MQTT (assinado pela CA)
- **server.key** - Chave privada do servidor MQTT
- **openssl.cnf** - Configuração OpenSSL com Subject Alternative Names (SANs)
- **generate_certs.sh** - Script para gerar os certificados

## Como Regenerar os Certificados

Se você precisar regenerar os certificados (por exemplo, se expiraram ou se mudou a configuração):

```bash
cd certs
bash generate_certs.sh
```

## Subject Alternative Names (SANs)

Os certificados foram configurados com os seguintes SANs:
- DNS: `mqtt` (nome do container MQTT broker)
- DNS: `localhost`
- DNS: `mosquitto`
- DNS: `grpc_server` (nome do container gRPC server)
- IP: `127.0.0.1`

Isso permite que os clientes se conectem aos serviços usando qualquer um desses nomes/IPs.

## Configuração nos Clientes

### MQTT Logger (Python - paho-mqtt)
```python
client.tls_set(
    ca_certs="/certs/ca.crt",
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS
)
```

### Gateway MQTT (Python - paho-mqtt publish)
```python
publish.single(
    topic,
    payload,
    hostname=MQTT_HOST,
    port=8883,
    tls={
        "ca_certs": "/certs/ca.crt",
        "cert_reqs": ssl.CERT_REQUIRED,
        "tls_version": ssl.PROTOCOL_TLS
    }
)
```

## Troubleshooting

### Erro: `certificate verify failed: self-signed certificate`
Este erro ocorre quando:
1. Os certificados não foram gerados corretamente
2. O certificado do servidor não tem SANs
3. O certificado não foi assinado pela CA correta

**Solução**: Execute `bash generate_certs.sh` para regenerar os certificados.

### Erro: `tlsv1 alert unknown ca`
Este erro ocorre quando o cliente não confia no CA do servidor.

**Solução**: Certifique-se de que:
1. O arquivo `ca.crt` está montado corretamente no container
2. O caminho para `ca.crt` está correto no código
3. O certificado do servidor foi assinado pela mesma CA

## Validade

Os certificados são válidos por **365 dias** a partir da data de geração.

Para verificar a validade:
```bash
openssl x509 -in server.crt -noout -dates
```

Para verificar os SANs:
```bash
openssl x509 -in server.crt -text -noout | grep -A2 "Subject Alternative Name"
```

Para verificar a cadeia de certificados:
```bash
openssl verify -CAfile ca.crt server.crt
```
