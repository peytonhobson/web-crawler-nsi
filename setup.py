from setuptools import setup, find_packages

setup(
    name="web_crawler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "crawl4ai>=0.1.0",
        "python-dotenv>=1.0.0",
        "pinecone-client>=6.0.0",
        "spacy>=3.7.2",
        "langchain>=0.1.0",
        "beautifulsoup4>=4.12.0",
        "markdown>=3.5.0",
        "html2text>=2020.1.16",
        "tqdm>=4.66.0",
        "requests>=2.31.0",
        "urllib3>=2.0.0",
        "python-slugify>=8.0.0",
        "openai>=1.0.0",
        "sentence-transformers>=2.2.0",
        "loguru>=0.7.0",
    ],
    python_requires=">=3.9",
    description="Web crawler with vector database integration for RAG applications",
    author="",
    author_email="",
)
