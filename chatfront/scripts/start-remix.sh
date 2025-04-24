#!/bin/bash

set -e

cd /chatfront

echo "Starting Remix application..."
echo "Environment: $NODE_ENV"
echo "Port: $PORT"
echo "Host: $HOST"
echo "CHATBACK_URL: $CHATBACK_URL"

# Check if build directory exists
if [ ! -d "/chatfront/build" ]; then
    echo "Error: Build directory not found!"
    exit 1
fi

# Check if required files exist
if [ ! -f "/chatfront/build/index.js" ]; then
    echo "Error: Build files not found!"
    exit 1
fi

# List installed packages
echo "Installed packages:"
bun pm ls

# Start the application
exec bun run start