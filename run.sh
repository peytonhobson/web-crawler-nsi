#!/bin/bash

# Navigate to the project directory (if needed)
cd "$(dirname "$0")"

# Run with the virtual environment's Python interpreter
./venv/bin/python orchestrator.py "$@" 