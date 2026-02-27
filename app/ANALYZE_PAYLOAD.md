# Payload Analysis Tool

Script para análise da relação entre tamanho de payload e latência.

## Instalação

```bash
pip install pandas matplotlib seaborn psycopg2-binary scipy
```

## Uso

### Conectar ao banco de dados local

Se estiver rodando o PostgreSQL em Docker:

```bash
# Certifique-se de que o PostgreSQL está rodando
docker compose ps

# Execute a análise
python analyze_payload.py
```

### Conectar a banco de dados remoto

```bash
# Configure as variáveis de ambiente
export DB_HOST=seu_host
export DB_NAME=iotlab
export DB_USER=iot
export DB_PASSWORD=iot
export DB_PORT=5433

# Execute a análise
python analyze_payload.py
```

## Gráficos Gerados

O script gera os seguintes gráficos em `results/payload_analysis/`:

### 1. `latency_vs_payload_scatter.png`
- **Tipo**: Scatter plot
- **Descrição**: Mostra a relação entre tamanho do payload e latência
- **Útil para**: Identificar tendências e outliers

### 2. `latency_by_category_boxplot.png`
- **Tipo**: Box plot
- **Descrição**: Distribuição de latência por categoria de tamanho
- **Útil para**: Comparar variabilidade entre protocolos

### 3. `avg_latency_by_category.png`
- **Tipo**: Bar plot
- **Descrição**: Latência média por categoria de tamanho
- **Útil para**: Comparação direta entre protocolos

### 4. `latency_per_byte.png`
- **Tipo**: Bar plot
- **Descrição**: Eficiência do protocolo (latência por byte)
- **Útil para**: Avaliar overhead do protocolo

### 5. `latency_vs_payload_regression.png`
- **Tipo**: Scatter com regressão linear
- **Descrição**: Relação linear entre payload e latência
- **Útil para**: Prever latência para diferentes tamanhos

### 6. `latency_heatmap.png`
- **Tipo**: Heatmap
- **Descrição**: Matriz de latência média
- **Útil para**: Visão geral rápida de performance

### 7. `latency_timeseries.png`
- **Tipo**: Série temporal
- **Descrição**: Evolução da latência ao longo do tempo
- **Útil para**: Identificar padrões temporais e degradação

## Arquivos CSV Exportados

### `payload_latency_summary.csv`
Estatísticas agregadas por cenário e categoria:
- Contagem de mensagens
- Média, desvio padrão, min, mediana, max de latência
- Tamanhos de payload (média, min, max)

### `payload_latency_detailed.csv`
Dados detalhados para análises customizadas:
- Cenário (protocolo + TLS)
- Tamanho do payload
- Categoria do payload
- Latência
- Timestamp

## Categorias de Payload

O script agrupa payloads em categorias:

| Categoria | Range | Uso Típico |
|-----------|-------|------------|
| **<500B** | 0-500 bytes | Sensores simples |
| **500B-1KB** | 500-1000 bytes | Sensores padrão |
| **1KB-2KB** | 1-2 KB | Múltiplos sensores |
| **2KB-5KB** | 2-5 KB | Dados enriquecidos |
| **>5KB** | >5 KB | Imagens, áudio |

## Métricas Calculadas

### Correlação
- Correlação de Pearson entre tamanho de payload e latência
- Calculada por cenário e geral

### Estatísticas Descritivas
- **Count**: Número de mensagens
- **Mean**: Latência média
- **Std**: Desvio padrão
- **Min/Max**: Valores extremos
- **Median**: Mediana (50º percentil)

### Eficiência
- **Latency per Byte**: Razão latência/tamanho
- Quanto menor, mais eficiente o protocolo

## Exemplo de Análise

```bash
# 1. Execute experimentos com diferentes payloads
docker compose --env-file .env.small_payload up --duration 60s
docker compose --env-file .env.large_payload up --duration 60s

# 2. Execute a análise
python analyze_payload.py

# 3. Veja os resultados
ls results/payload_analysis/
```

## Interpretação dos Resultados

### MQTT vs gRPC

**MQTT** geralmente tem:
- ✅ Menor latência para payloads pequenos
- ✅ Overhead menor para mensagens simples
- ❌ Cresce linearmente com o tamanho

**gRPC** geralmente tem:
- ❌ Overhead inicial maior (protobuf)
- ✅ Serialização mais eficiente para dados estruturados
- ✅ Melhor performance com payloads grandes

### TLS vs Plain

Com **TLS**:
- ❌ Adiciona overhead constante (handshake)
- ❌ Latência base maior (~5-20ms)
- ✅ Mas cresce proporcionalmente igual

### Latência per Byte

- Valores baixos = protocolo eficiente
- Deve **diminuir** com payloads maiores (overhead amortizado)
- Se **aumenta**, indica saturação ou problema de rede

## Troubleshooting

### Erro: "Database connection failed"

```bash
# Verifique se o PostgreSQL está rodando
docker compose ps

# Ou inicie apenas o banco
docker compose up postgres -d
```

### Erro: "No data found"

```bash
# Execute experimentos primeiro
docker compose --env-file .env.mqtt_plain up --build
# Aguarde alguns segundos para coletar dados
# Ctrl+C para parar
```

### Erro: "Module not found"

```bash
# Instale as dependências
pip install pandas matplotlib seaborn psycopg2-binary scipy
```

## Análise Avançada

Para análises customizadas, use os dados exportados:

```python
import pandas as pd

# Carregar dados detalhados
df = pd.read_csv('results/payload_analysis/payload_latency_detailed.csv')

# Exemplo: Filtrar apenas MQTT
mqtt_data = df[df['protocol'] == 'mqtt']

# Exemplo: Comparar TLS vs Plain
import matplotlib.pyplot as plt
df.boxplot(column='latency_ms', by='use_tls')
plt.show()
```

## Dicas

1. **Execute experimentos longos**: Mais dados = resultados mais confiáveis
2. **Varie os tamanhos**: Use diferentes configurações de payload
3. **Controle variáveis**: Execute um protocolo por vez para isolar efeitos
4. **Compare consistentemente**: Use mesma duração e condições
5. **Documente condições**: Network simulation on/off, máquina, etc.
