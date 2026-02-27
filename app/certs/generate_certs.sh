#!/bin/bash

# Script to generate TLS certificates for MQTT broker and clients
# This creates a self-signed CA and server certificate with proper SANs

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔐 Generating TLS certificates for MQTT..."

# Clean up old certificates
echo "🧹 Cleaning up old certificates..."
rm -f ca.key ca.crt ca.srl
rm -f server.key server.csr server.crt
rm -f index.txt serial

# Create necessary files for CA operations
touch index.txt
echo "01" > serial

# 1. Generate CA private key
echo "📝 Step 1/4: Generating CA private key..."
openssl genrsa -out ca.key 2048

# 2. Generate self-signed CA certificate
echo "📝 Step 2/4: Generating self-signed CA certificate..."
openssl req -new -x509 -days 365 \
    -key ca.key \
    -out ca.crt \
    -subj "//CN=Test CA" \
    -extensions v3_ca \
    -config openssl.cnf

# 3. Generate server private key
echo "📝 Step 3/4: Generating server private key..."
openssl genrsa -out server.key 2048

# 4. Generate server certificate signing request
echo "📝 Step 4/4: Generating server CSR and certificate..."
openssl req -new \
    -key server.key \
    -out server.csr \
    -config openssl.cnf

# 5. Sign server certificate with CA (with extensions)
openssl x509 -req -days 365 \
    -in server.csr \
    -CA ca.crt \
    -CAkey ca.key \
    -CAcreateserial \
    -out server.crt \
    -extensions v3_req \
    -extfile openssl.cnf

echo ""
echo "✅ Certificates generated successfully!"
echo ""
echo "📋 Certificate details:"
echo "   CA Certificate: ca.crt"
echo "   CA Private Key: ca.key"
echo "   Server Certificate: server.crt"
echo "   Server Private Key: server.key"
echo ""
echo "🔍 Verifying server certificate..."
openssl x509 -in server.crt -text -noout | grep -A2 "Subject Alternative Name" || echo "⚠️  Warning: No SANs found!"
echo ""
echo "🔍 Verifying certificate chain..."
openssl verify -CAfile ca.crt server.crt
echo ""
echo "✨ Done!"
