#!/bin/sh
set -e

echo "Generating env.js..."
envsubst < /usr/share/nginx/html/env.template.js > /usr/share/nginx/html/env.js

echo "Generating nginx default.conf"
envsubst '$API_HOST' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting nginx..."
exec nginx -g "daemon off;"