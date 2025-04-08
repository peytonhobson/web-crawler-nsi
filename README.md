# Web Crawler with Vector Database Integration

This project implements a web crawler that processes content and stores it in a vector database (Pinecone) for efficient semantic search capabilities.

## Features

- Web crawling with configurable parameters
- Text chunking and processing
- Vector embeddings generation
- Pinecone vector database integration
- Namespace-based content organization
- Duplicate detection and handling
- Robust error handling and logging
- Automated orchestration of crawling and vector database updates

## Prerequisites

- Python 3.8+
- Pinecone API access
- OpenAI API access (if using OpenAI embeddings)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd web-crawler
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration values
   - Adjust optional parameters as needed

## Configuration

See `.env.example` for detailed configuration options. Key variables include:

- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI embeddings)
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_ENVIRONMENT`: Pinecone environment (e.g., us-east-1-aws)
- `PINECONE_INDEX_NAME`: Name of your Pinecone index
- `CUSTOMER_ID`: Unique identifier for namespace creation

## Usage

### Automated Process (Recommended)

The orchestrator script (`orchestrator.py`) provides a seamless way to run the entire pipeline:

```bash
python orchestrator.py
```

This will:
1. Run the crawler to fetch website content
2. Process and chunk the content
3. Generate embeddings
4. Upload to Pinecone with rich metadata

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
- Keywords are automatically extracted
- Content is filtered for relevance
- Duplicates are detected and handled

## Error Handling

The system includes robust error handling for:
- API rate limits
- Network issues
- Invalid content
- Duplicate records
- Vector dimension mismatches

## Logging

Detailed logging is implemented for:
- Crawling progress
- Content processing
- Vector uploads
- Error tracking

Logs are stored in the `logs` directory with timestamps:
- Crawler logs: `logs/crawler_[timestamp].log`
- Upload logs: `logs/upload_[timestamp].log`
- Orchestrator logs: `logs/orchestrator_[timestamp].log`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here]