#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "No .env file found. Please create one from env_example"
    exit 1
fi

while true; do
    PYTHONUNBUFFERED=1 python3 movies.py >> log.txt 2>&1
    echo "[$(date)] Bot exited, restarting in 10 seconds..." >> log.txt
    sleep 10
done
