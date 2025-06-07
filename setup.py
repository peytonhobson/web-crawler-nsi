from setuptools import setup, find_packages

setup(
    name="web_crawler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "crawl4ai~=0.6.0",
        "python-dotenv~=1.0.0",
        "pinecone~=6.0.0",
        "langchain~=0.3.0",
        "openai>=1.68.2,<2.0.0",
        "playwright~=1.49.0",
        "asyncio~=3.4.0",
        "langchain-experimental~=0.3.0",
        "langchain-openai~=0.3.0",
        "sendgrid~=6.10.0",
        "beautifulsoup4~=4.12.0",
    ],
    python_requires="~=3.9",
    description=("Web crawler with VectorDB integration for RAG apps"),
    author="",
    author_email="",
)
