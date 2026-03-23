#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${ROOT_DIR}/frontend/certs"

CA_KEY="${CERT_DIR}/ledger-local-ca.key"
CA_CERT="${CERT_DIR}/ledger-local-ca.crt"
SERVER_KEY="${CERT_DIR}/ledger-app.key"
SERVER_CSR="${CERT_DIR}/ledger-app.csr"
SERVER_CERT="${CERT_DIR}/ledger-app.crt"
SERVER_EXT="${CERT_DIR}/ledger-app.ext"

mkdir -p "${CERT_DIR}"

if [[ ! -f "${CA_KEY}" || ! -f "${CA_CERT}" ]]; then
  echo "Generating local dev CA..."
  openssl genrsa -out "${CA_KEY}" 4096 >/dev/null 2>&1
  openssl req -x509 -new -nodes -key "${CA_KEY}" -sha256 -days 3650 \
    -out "${CA_CERT}" \
    -subj "/C=IN/ST=Local/L=Local/O=Ledger App/OU=Development/CN=Ledger App Local Dev CA" >/dev/null 2>&1
else
  echo "Using existing local dev CA."
fi

cat > "${SERVER_EXT}" <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=localhost
IP.1=127.0.0.1
IP.2=::1
EOF

echo "Generating localhost server certificate..."
openssl genrsa -out "${SERVER_KEY}" 2048 >/dev/null 2>&1
openssl req -new -key "${SERVER_KEY}" -out "${SERVER_CSR}" \
  -subj "/C=IN/ST=Local/L=Local/O=Ledger App/OU=Development/CN=localhost" >/dev/null 2>&1
openssl x509 -req -in "${SERVER_CSR}" -CA "${CA_CERT}" -CAkey "${CA_KEY}" \
  -CAcreateserial -out "${SERVER_CERT}" -days 825 -sha256 \
  -extfile "${SERVER_EXT}" >/dev/null 2>&1

chmod 600 "${CA_KEY}" "${SERVER_KEY}"

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "Adding local dev CA to macOS login keychain (may prompt for password)..."
  security add-trusted-cert -d -r trustRoot \
    -k "${HOME}/Library/Keychains/login.keychain-db" "${CA_CERT}" || true
fi

echo

echo "HTTPS certificates are ready:"
echo "  CA:      ${CA_CERT}"
echo "  Server:  ${SERVER_CERT}"
echo "  Key:     ${SERVER_KEY}"
echo
echo "Next steps:"
echo "  1) docker compose up -d --build frontend"
echo "  2) Open https://localhost"
