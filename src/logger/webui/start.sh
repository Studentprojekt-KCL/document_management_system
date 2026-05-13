#!/bin/sh
set -e

if [ -z "$LOGWEB_ADDR" ]; then
  echo "ERROR: LOGWEB_ADDR is not set" >&2
  exit 1
fi

if [ -z "$LOGWEB_BIND" ]; then
  echo "ERROR: LOGWEB_BIND is not set" >&2
  exit 1
fi

echo "Starting Fresh server on port $LOGWEB_BIND (LOGWEB_ADDR=$LOGWEB_ADDR)..."
exec deno serve -A --port="$LOGWEB_BIND" _fresh/server.js