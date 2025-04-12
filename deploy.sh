#!/bin/bash
# Deployment script for web crawler using Docker

# Ensure the script stops on first error
set -e

# Create required directories if they don't exist
mkdir -p cleaned_output
mkdir -p logs

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found. Please create one from .env.example"
  exit 1
fi

# Check for OpenAI API key in .env
if ! grep -q "OPENAI_API_KEY" .env; then
  echo "Error: OPENAI_API_KEY not found in .env file"
  exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker-compose build

# Run the crawler with arguments passed to this script
echo "Starting web crawler..."
docker-compose run --rm crawler python orchestrator.py "$@"

echo "Crawler run complete! Check the logs/ and cleaned_output/ directories for results." 