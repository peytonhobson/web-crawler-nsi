#!/bin/bash
# Deployment script for running on Render

# Create directories on the persistent disk
mkdir -p /var/data/output
mkdir -p /var/data/logs

echo "Starting web crawler on Render in HTTP-only mode..."

# Make sure we're using HTTP-only mode
export USE_BROWSER=false

# Run with the Render-optimized configuration
python orchestrator.py --config examples/render_config.yaml "$@"

echo "Crawler run complete! Check the /var/data/output and /var/data/logs directories for results." 