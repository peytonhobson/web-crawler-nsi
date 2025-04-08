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

1. Run the crawler:
```bash
python crawler/main.py
```

2. Process and upload content:
```bash
python process_and_upload.py
```

## Vector Database Structure

- Each customer's content is stored in a dedicated namespace
- Namespace format: `web_crawl_{CUSTOMER_ID}`
- Vector IDs include chunk information to prevent duplicates
- Metadata includes source URL, timestamp, and content information

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here]