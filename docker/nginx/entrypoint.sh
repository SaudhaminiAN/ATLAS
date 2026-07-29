#!/bin/sh
set -e

CERT="${SSL_CERT_PATH:-/etc/nginx/ssl/cert.pem}"
KEY="${SSL_KEY_PATH:-/etc/nginx/ssl/key.pem}"

if [ "${SSL_ENABLED}" = "true" ] && [ -f "$CERT" ] && [ -f "$KEY" ]; then
  cp /etc/nginx/templates/https.conf /etc/nginx/conf.d/default.conf
else
  cp /etc/nginx/templates/http-only.conf /etc/nginx/conf.d/default.conf
fi

exec nginx -g 'daemon off;'
