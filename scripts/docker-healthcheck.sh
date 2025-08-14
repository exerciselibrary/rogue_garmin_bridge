#!/bin/bash

# Docker health check script for Rogue Garmin Bridge
# This script is used by Docker's HEALTHCHECK instruction

set -e

# Configuration
HEALTH_URL="http://localhost:5000/health"
TIMEOUT=10
MAX_RETRIES=3

# Function to check health endpoint
check_health() {
    local retry=0
    
    while [ $retry -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time $TIMEOUT "$HEALTH_URL" > /dev/null 2>&1; then
            echo "Health check passed"
            return 0
        fi
        
        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            echo "Health check failed, retrying ($retry/$MAX_RETRIES)..."
            sleep 2
        fi
    done
    
    echo "Health check failed after $MAX_RETRIES attempts"
    return 1
}

# Perform health check
check_health