# Web Crawler with Vector Database Integration

This project implements a web crawler that processes content from websites and stores it in a vector database for efficient semantic search capabilities. It's designed for crawling winery websites and organizing their content for RAG (Retrieval-Augmented Generation) applications.

## Features

- Specialized content crawling using crawl4ai
- Intelligent content filtering using OpenAI models
- Advanced web crawling with configurable depth
- Duplicate link detection
- JavaScript execution for handling dynamic content
- Markdown content generation
- Robust error handling and logging

## Prerequisites

- Python 3.9+
- OpenAI API access (for content filtering)
- crawl4ai library for web crawling

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web-crawler.git
cd web-crawler
```

2. Set up a virtual environment:
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
# Install required packages
pip install -r requirements.txt
```

4. Install the package in development mode to handle absolute imports:
```bash
# This allows the project's absolute imports to work correctly
pip install -e .
```

5. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```
   - Adjust other configuration parameters as needed

## Configuration

The crawler is configured in `crawler/crawl.py` and uses the following key components:

- **AsyncWebCrawler**: Main crawler engine from crawl4ai
- **BFSDeepCrawlStrategy**: Implements breadth-first search for crawling links
- **LXMLWebScrapingStrategy**: Strategy for extracting content from web pages
- **LLMContentFilter**: Uses OpenAI models to filter and format content
- **DefaultMarkdownGenerator**: Generates Markdown from filtered content

Key configuration options:
- `max_depth`: Controls how deep the crawler will follow links (currently set to 0 for base pages)
- Content filter instructions for extracting quality content
- URL processing and canonicalization
- Batch processing to manage resource usage

## Usage

To run the crawler:

```bash
# Since the package is installed in development mode, you can run it directly
python -m crawler.crawl
```

This will:
1. Fetch the initial set of links from the specified starting URL
2. Filter and process these links to find unique internal URLs
3. Crawl each unique URL in batches
4. Filter and process the content using the LLM content filter
5. Generate clean markdown output for each page
6. Return the processed results

## Production Deployment

For production environments, follow these best practices:

### Installation

Instead of development mode installation, install the package properly:

1. Create a `setup.py` file in the root directory if it doesn't exist:
```python
from setuptools import setup, find_packages

setup(
    name="web-crawler",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "crawl4ai",
        "openai",
        "python-dotenv",
        # Add other dependencies from requirements.txt
    ],
)
```

2. Build and install the package:
```bash
pip install .
```

### Environment Configuration

There are several approaches to managing environment variables in production, each with its own advantages:

#### Option 1: Using `.env` files (Simple Setup)

`.env` files can be used in production with proper security measures:

```bash
# Create a .env file with restricted permissions
touch .env
chmod 600 .env  # Only the owner can read/write

# Add your environment variables
echo "OPENAI_API_KEY=your_api_key_here" >> .env
```

**Security considerations:**
- Store `.env` files outside of version control
- Use restricted file permissions
- Consider encrypting the file when not in use
- Establish a secure process for deploying `.env` files

#### Option 2: System Environment Variables (Recommended for many deployments)

Use system-level environment variables:

```bash
export OPENAI_API_KEY=your_api_key_here
# Add any other required environment variables
```

Add to startup scripts for persistence:
```bash
# Add to ~/.bashrc or ~/.bash_profile for persistence
echo 'export OPENAI_API_KEY=your_api_key_here' >> ~/.bashrc
```

#### Option 3: Container Environment Variables

For containerized deployments (e.g., Docker):

```bash
# When running the container
docker run -e OPENAI_API_KEY=your_api_key_here web-crawler

# Or using an env file with Docker
docker run --env-file .env web-crawler
```

#### Option 4: Secrets Management Systems (Enterprise)

For enterprise environments, use a dedicated secrets management system:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

These provide enhanced security features like:
- Encryption at rest and in transit
- Access controls and auditing
- Automatic rotation
- Integration with identity management

Choose the approach that best fits your security requirements and operational complexity.

### Containerization

Using Docker for containerization:

1. Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir .

CMD ["python", "-m", "crawler.crawl"]
```

2. Build and run the container:
```bash
docker build -t web-crawler .
docker run -e OPENAI_API_KEY=your_api_key_here web-crawler
```

### Error Handling and Logging

For production, enhance the error handling and logging:

1. Add structured logging to a file:
```python
import logging

logging.basicConfig(
    filename='crawler.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

2. Implement proper exception handling with retry mechanisms for transient failures.

### Performance Optimization

1. Adjust batch size and concurrency based on your infrastructure:
   - For higher-end servers, increase batch size
   - For limited resources, decrease concurrency

2. Consider implementing rate limiting to respect website policies:
```python
# Add delay between requests
config = CrawlerRunConfig(
    # existing config...
    request_delay=1.0,  # 1 second delay between requests
)
```

### Monitoring

1. Implement health checks to monitor crawler performance
2. Add metrics collection for:
   - Pages crawled
   - Success/failure rates
   - Processing time
   - API usage (for OpenAI)

3. Setup alerts for critical failures

### Scheduling

For periodic crawling, use a scheduling system:

1. Simple scheduling with cron:
```bash
# Run crawler every day at 2 AM
0 2 * * * cd /path/to/web-crawler && python -m crawler.crawl
```

2. For more complex workflows, consider Airflow or similar orchestration tools.

## Project Structure

```
web-crawler/
├── crawler/
│   ├── __init__.py
│   ├── crawl.py          # Main crawler implementation
│   ├── sanitize_filename.py
│   └── clean_markdown.py
├── setup.py              # Package installation configuration
├── requirements.txt      # Project dependencies
└── .env                  # Environment variables (create from .env.example)
```

## Environmental Variables

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key for content filtering

## Advanced Configuration

You can modify the crawler behavior by editing the configuration in `crawler/crawl.py`:

- Change the starting URL (currently set to "https://www.westhillsvineyards.com/wines")
- Adjust crawl depth for more comprehensive content collection
- Modify batch size for performance tuning
- Update content filtering instructions
- Add specific tag exclusions
- Configure JavaScript code for DOM manipulation before crawling

## Troubleshooting

If you encounter import errors when running the crawler:

1. Ensure you've installed the package in development mode:
   ```bash
   pip install -e .
   ```

2. Verify that your virtual environment is activated:
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. Check that the project structure follows the expected pattern with proper `__init__.py` files in each directory.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

