Página oficial do protobuff para Windows: https://github.com/protocolbuffers/protobuf/releases

- Realizar o download do binário https://github.com/protocolbuffers/protobuf/releases/download/v34.0/protoc-34.0-win64.zip
- Extraia o binário e salve na raiz de C:/ com o nome de "protobuf"
- Inclua ao PATH do Windows o path C:\protobuf\bin\protoc.exe
- Reinicie o computador

Instale as dependências:

```shell
pip install grpcio grpcio-tools
```

Dentro da pasta, execute

```shell
python -m grpc_tools.protoc \
  -I. \
  --python_out=./generated \
  --grpc_python_out=./generated \
  sensor.proto
```