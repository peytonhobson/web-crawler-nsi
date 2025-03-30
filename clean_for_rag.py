import os
from pathlib import Path
import logging
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Make sure it's set in your .env file.")

# Create OpenAI client
client = OpenAI(api_key=api_key)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def clean_page_with_gpt4o(page_content, max_retries=3, delay=5):
    prompt = (
        "You are an assistant that extracts the core, meaningful content from a webpage. "
        "Remove navigation menus, repeated boilerplate (such as links, headers, footers, subscription prompts), "
        "and extraneous elements. Preserve all context, important Q&A sections, and details. "
        "Return the cleaned text only.\n\n"
        "Page content:\n\n"
        f"{page_content}\n\n"
        "Cleaned content:"
    )
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You extract meaningful content from webpages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                logging.info("Retrying in a few seconds...")
                time.sleep(delay)
    
    raise Exception("Failed cleaning page after multiple retries.")

def process_pages(input_dir, output_dir):
    input_directory = Path(input_dir)
    output_directory = Path(output_dir)
    output_directory.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_directory.glob("*.md"))
    logging.info(f"Found {len(md_files)} Markdown files to process.")

    for file_path in md_files:
        try:
            logging.info(f"Processing {file_path.name}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                page_content = f.read()

            cleaned_content = clean_page_with_gpt4o(page_content)

            cleaned_filename = file_path.stem + "_cleaned" + file_path.suffix
            output_file = output_directory / cleaned_filename

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            logging.info(f"Saved cleaned content to {output_file}")
        except Exception as e:
            logging.error(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    input_directory = "c:/Users/james/Downloads/web crawler"
    output_directory = "c:/Users/james/Downloads/cleaned_output"
    process_pages(input_directory, output_directory)
