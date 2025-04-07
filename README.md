# Web Crawler and Content Processor

This project crawls websites, processes the content, and uploads it to Pinecone for vector search capabilities.

## Setup Instructions

1. Create a Python virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_index_name
CUSTOMER_ID=your_customer_id
```

## Usage

1. Run the crawler:
```bash
python crawl.py
```

2. Process and upload to Pinecone:
```bash
python upload_to_pinecone.py
```

For dry run mode (process but don't upload):
```bash
python upload_to_pinecone.py --dry
```

## Project Structure

- `crawl.py`: Main crawler script
- `clean_markdown.py`: Markdown processing utilities
- `sanitize_filename.py`: Filename sanitization utilities
- `upload_to_pinecone.py`: Pinecone upload script 