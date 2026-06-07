# Docker variant for Render — use this if the native Python environment is
# missing Chromium's system libraries (errors like
# "error while loading shared libraries: libnss3.so").
#
# The official Playwright image ships Chromium + all required OS deps, and
# already sets PLAYWRIGHT_BROWSERS_PATH=/ms-playwright (do NOT override it).
#
# To use on Render: set the service to a Docker environment pointing at this
# file (see the commented "Docker alternative" block in render.yaml), and drop
# the PLAYWRIGHT_BROWSERS_PATH env var.
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the project
COPY . .
RUN pip install -e .

# Browsers are preinstalled in the base image; ensure Chromium is present
RUN python -m playwright install chromium

CMD ["python", "orchestrator.py"]
