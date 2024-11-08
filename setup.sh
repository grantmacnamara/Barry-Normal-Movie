#!/bin/bash

# Make start.sh executable
chmod +x start.sh

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp env_example .env
    echo "Please edit .env file with your credentials before starting the bot"
fi

# Create seen_posts.txt if it doesn't exist
touch seen_posts.txt

# Build and start the Docker container
docker-compose up --build -d 