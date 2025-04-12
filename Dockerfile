# Use the official Playwright image as base (includes browsers pre-installed)
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV USE_BROWSER=true

# Default command runs the orchestrator
CMD ["python", "orchestrator.py"] 