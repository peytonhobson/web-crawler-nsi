# Web Crawler with Vector Database Integration

This project implements a web crawler that processes content and stores it in a vector database (Pinecone) for efficient semantic search capabilities. It's specifically designed for crawling winery websites and organizing their content for RAG (Retrieval-Augmented Generation) applications.

## Features

- Specialized content crawling
- Intelligent content filtering using GPT-4
- Text chunking and processing with spaCy
- Vector embeddings generation (using Pinecone's hosted models)
- Pinecone vector database integration
- Namespace-based content organization
- Duplicate detection and handling
- Robust error handling and logging
- Automated orchestration of crawling and vector database updates

## Prerequisites

- Python 3.9+
- Pinecone API access
- OpenAI API access (for content filtering and embeddings)
- crawl4ai library for web crawling
- langchain for RAG-based operations
- Vector embedding models (support for OpenAI or sentence-transformers)
- spaCy with en_core_web_sm model (included in requirements.txt)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
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
# venv\Scripts\activate
```

3. Install dependencies:
```bash
# Install required packages
pip install -r requirements.txt

# Note: The en_core_web_sm model is included in requirements.txt
# and should be installed automatically
```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration values
   - Adjust optional parameters as needed

## Configuration

See `.env.example` for detailed configuration options. Key variables include:

- `OPENAI_API_KEY`: Your OpenAI API key (required for content filtering)
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_ENVIRONMENT`: Pinecone environment (e.g., us-east-1-aws)
- `PINECONE_INDEX_NAME`: Name of your Pinecone index
- `CUSTOMER_ID`: Unique identifier for namespace creation (e.g., "winery-name")
- `PINECONE_HOST`: Direct host URL for better performance
- `EMBEDDING_MODEL`: Model to use for embeddings (e.g., "llama-text-embed-v2")
- `CHUNK_SIZE`: Size of text chunks (default: 500)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 50)

## Usage

### Automated Process (Recommended)

The orchestrator script (`orchestrator.py`) provides a seamless way to run the entire pipeline:

```bash
python orchestrator.py
```

This will:
1. Run the crawler to fetch winery website content
2. Filter content using GPT-4 for relevance
3. Process and chunk the content using spaCy
4. Generate embeddings using Pinecone's hosted models
5. Upload to Pinecone with rich metadata

The orchestrator includes:
- Automatic logging to `logs/orchestrator_[timestamp].log`
- Error handling and recovery
- Progress tracking
- Namespace management
- Metadata enrichment

### Manual Process

If you prefer to run the steps separately:

1. Run the crawler:
```bash
python crawler/crawl.py
```

2. Process and upload content:
```bash
python vectordb/upload_to_pinecone_v2.py
```

### Virtual Environment Maintenance

For managing your virtual environment:

- **Activating**: Always activate the virtual environment before running commands
  ```bash
  source venv/bin/activate  # On macOS/Linux
  # venv\Scripts\activate   # On Windows
  ```

- **Development Mode Install**: Install the project in development mode
  ```bash
  pip install -e .
  ```
  This allows you to import modules from anywhere in the codebase without path manipulation

- **Updating dependencies**: If requirements.txt changes, update your environment
  ```bash
  pip install -r requirements.txt
  ```

- **Deactivating**: When finished, deactivate the virtual environment
  ```bash
  deactivate
  ```

- **Dependencies**: To see installed packages in your environment
  ```bash
  pip list
  ```

## Vector Database Structure

Each record in Pinecone includes:

### Core Metadata
- Source information (URL, domain, path)
- Content information (text, keywords, token count)
- Chunk information (ID, index, name)
- Tracking information (timestamps, batch ID)
- Customer information

### Namespace Organization
- Each customer's content is stored in a dedicated namespace
- Namespace format: `web_crawl_{CUSTOMER_ID}`
- Vector IDs include chunk information to prevent duplicates
- Metadata includes source URL, timestamp, and content information

### Content Processing
- Text is chunked with configurable overlap
- Keywords are automatically extracted using spaCy
- Content is filtered for relevance using GPT-4
- Duplicates are detected using content hashing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

