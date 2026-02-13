#!/bin/sh
set -e
export PORT="${PORT:-8080}"
export API_URL="${API_URL:-http://localhost:8000}"
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
envsubst '${API_URL}' < /etc/nginx/config.js.template > /usr/share/nginx/html/config.js
exec nginx -g "daemon off;"
