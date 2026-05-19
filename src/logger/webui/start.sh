#!/bin/sh
set -e

if [ -z "$LOGWEB_BIND_ADDR" ]; then
  echo "ERROR: LOGWEB_BIND_ADDR is not set" >&2
  exit 1
fi

if [ -z "$LOGWEB_BIND_PORT" ]; then
  echo "ERROR: LOGWEB_BIND_PORT is not set" >&2
  exit 1
fi

if [ -z "$LOGWEB_API_URL" ]; then
  echo "ERROR: LOGWEB_API_URL is not set" >&2
  exit 1
fi

echo "Starting Fresh server on $LOGWEB_BIND_ADDR:$LOGWEB_BIND_PORT (API=$LOGWEB_API_URL)..."
exec deno serve -A --host="$LOGWEB_BIND_ADDR" --port="$LOGWEB_BIND_PORT" _fresh/server.js