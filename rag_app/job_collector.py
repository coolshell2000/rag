#!/usr/bin/env python3
"""
Job Collector Script

This script reads job URLs from a file (job_urls.txt) and crawls each job posting,
extracting and storing job information in the database.

Usage:
    python job_collector.py

The script expects a file named 'job_urls.txt' in the same directory,
with one job URL per line.
"""

import os
import sys
import time
from typing import List

# Import existing functions
from main import print_all_jobs
from scraper import split_into_chunks_from_url
from rag import extract_job_info
from database import create_job_database, save_job_to_db
from rag import generate

def summarize_job_description(description: str) -> str:
    """Uses RAG to create a concise summary of the job description."""
    if not description:
        return ""

    # Create a query to summarize the job description
    query = "Please provide a concise summary of this job description focusing on the key responsibilities and requirements."

    # Split the description into chunks if it's too long
    max_length = 10000  # Max length for a single chunk
    if len(description) > max_length:
        # Split into smaller chunks
        chunks = [description[i:i+max_length] for i in range(0, len(description), max_length)]
    else:
        chunks = [description]

    try:
        # Generate a summary using the RAG pipeline
        summary = generate(query, chunks)
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Return original description if summarization fails
        return description

def scrape_and_store_job_with_rag(url: str):
    """Scrapes a job posting from URL, uses RAG to extract structured info, and stores it in the database."""
    print(f"Scraping job from {url}...")
    try:
        chunks = split_into_chunks_from_url(url)
        print(f"Extracted {len(chunks)} chunks from webpage")

        print("Using RAG to extract structured job information...")
        job_data = extract_job_info(chunks)

        if not job_data:
            print("RAG extraction failed, falling back to simple parsing...")
            from database import parse_job_chunks
            job_data = parse_job_chunks(chunks)
            print("Fallback parsing completed")

        if job_data:
            # Use RAG to summarize the job description if it exists
            if 'description' in job_data and job_data['description']:
                print("Using RAG to summarize job description...")
                original_description = job_data['description']
                summarized_description = summarize_job_description(original_description)

                # Only update if the summary is different and valid
                if summarized_description and summarized_description != original_description:
                    print("Job description summarized successfully!")
                    job_data['description'] = summarized_description
                else:
                    print("Using original job description (summary not needed or failed)")

            print("Creating database and storing job...")
            create_job_database()
            save_job_to_db(url, job_data)
            print("✓ Job stored in database successfully!")
            return True
        else:
            print("✗ Failed to extract job information")
            return False

    except Exception as e:
        print(f"✗ Error processing job: {e}")
        return False


def read_job_urls(file_path: str = "job_urls.txt") -> List[str]:
    """
    Reads job URLs from a text file.

    Args:
        file_path: Path to the file containing job URLs (one per line)

    Returns:
        List of URLs, stripped of whitespace and empty lines
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        print(f"Please create {file_path} with one job URL per line.")
        return []

    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                url = line.strip()
                if url and not url.startswith('#'):  # Skip empty lines and comments
                    urls.append(url)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

    return urls


def collect_jobs(urls: List[str], delay: float = 1.0) -> None:
    """
    Collects job information from multiple URLs, skipping already processed ones.

    Args:
        urls: List of job URLs to process
        delay: Delay between requests in seconds (to be respectful to servers)
    """
    if not urls:
        print("No URLs to process.")
        return

    # Get already processed URLs from database
    from database import get_all_jobs
    try:
        existing_jobs = get_all_jobs()
        processed_urls = {job['url'] for job in existing_jobs}
        print(f"Found {len(processed_urls)} already processed job(s) in database")
    except Exception as e:
        print(f"Warning: Could not check existing jobs in database: {e}")
        processed_urls = set()

    # Filter out already processed URLs
    urls_to_process = []
    skipped_urls = []

    for url in urls:
        if url in processed_urls:
            skipped_urls.append(url)
        else:
            urls_to_process.append(url)

    if skipped_urls:
        print(f"Skipping {len(skipped_urls)} already processed URL(s):")
        for url in skipped_urls:
            print(f"  ✓ {url}")

    if not urls_to_process:
        print("All URLs have already been processed. Nothing to do.")
        return

    print(f"\nProcessing {len(urls_to_process)} new URL(s)...")
    print("-" * 50)

    successful = 0
    failed = 0

    for i, url in enumerate(urls_to_process, 1):
        print(f"\n[{i}/{len(urls_to_process)}] Processing: {url}")

        try:
            success = scrape_and_store_job_with_rag(url)
            if success:
                successful += 1
                print(f"✓ Successfully processed job {i}")
            else:
                failed += 1
                print(f"✗ Failed to process job {i}")

        except Exception as e:
            print(f"✗ Failed to process job {i}: {e}")
            failed += 1

        # Add delay between requests to be respectful
        if i < len(urls_to_process) and delay > 0:
            print(f"Waiting {delay} second(s) before next request...")
            time.sleep(delay)

    print(f"\n{'='*50}")
    print("COLLECTION COMPLETE")
    print(f"Total URLs processed: {len(urls_to_process)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if skipped_urls:
        print(f"Skipped (already processed): {len(skipped_urls)}")
    print(f"{'='*50}")


def main():
    """Main function to run the job collector."""
    print("Job Collector Script")
    print("====================")

    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command in ['--view', '-v', 'view']:
            print("Viewing stored jobs...")
            print_all_jobs()
            return
        elif command in ['--help', '-h', 'help']:
            print("Usage:")
            print("  python job_collector.py              # Collect jobs from job_urls.txt")
            print("  python job_collector.py --view       # View stored jobs")
            print("  python job_collector.py --help       # Show this help")
            return
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information.")
            return

    # Default behavior: collect jobs
    # Read URLs from file
    urls = read_job_urls()

    if not urls:
        print("No valid URLs found. Exiting.")
        sys.exit(1)

    # Display URLs to be processed
    print(f"\nFound {len(urls)} job URL(s) to process:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")

    # Ask for confirmation
    try:
        response = input("\nProceed with collection? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Collection cancelled.")
            return
    except KeyboardInterrupt:
        print("\nCollection cancelled.")
        return

    # Collect jobs
    collect_jobs(urls)


if __name__ == "__main__":
    main()