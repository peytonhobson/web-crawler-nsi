from setuptools import setup, find_packages

setup(
    name="web_crawler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "crawl4ai>=0.1.0",
        "python-dotenv>=1.0.0",
        "pinecone>=6.0.0",
        "spacy>=3.7.2",
        "langchain>=0.1.0",
        "openai>=1.0.0",
    ],
    python_requires=">=3.9",
    description=("Web crawler with VectorDB integration for RAG apps"),
    author="",
    author_email="",
)
