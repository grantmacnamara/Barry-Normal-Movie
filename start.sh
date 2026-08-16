#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "No .env file found. Please create one from env_example"
    exit 1
fi

# Check if virtual environment exists
if [ ! -f .venv/bin/python3 ]; then
    echo "Error: .venv directory or python3 binary not found."
    exit 1
fi

while true; do
    PYTHONUNBUFFERED=1 .venv/bin/python3 movies.py >> log.txt 2>&1
    echo "[$(date)] Bot exited, restarting in 10 seconds..." >> log.txt
    sleep 10
done
