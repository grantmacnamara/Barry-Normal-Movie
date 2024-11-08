#!/bin/bash

# Check if .env file exists, if not create it from example
if [ ! -f .env ]; then
    echo "No .env file found. Creating from env_example..."
    cp env_example .env
    echo "Please update the .env file with your actual credentials"
    exit 1
fi

# Start the Python script
python movies.py 