#!/bin/sh
# Self-signed because public certificates aren't practical for a bare IP on a
# custom port. Kept in a volume so browsers' "proceed anyway" choice survives restarts.
set -e
CERT_DIR=/certs
mkdir -p "$CERT_DIR"
PUBLIC_IP="${PUBLIC_IP:-147.93.90.97}"
if [ ! -s "$CERT_DIR/server.crt" ] || [ ! -s "$CERT_DIR/server.key" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
        -subj "/CN=$PUBLIC_IP" -addext "subjectAltName=IP:$PUBLIC_IP"
fi
exec nginx -g 'daemon off;'
