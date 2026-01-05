import requests
from bs4 import BeautifulSoup
from typing import List

def split_into_chunks_from_url(url: str) -> List[str]:
    """Fetches a document from a URL, extracts plain text from HTML, and splits it into chunks based on double newlines."""
    # Use proper SSL certificate verification with timeout
    response = requests.get(url, verify=True, timeout=30)
    response.raise_for_status()
    content = response.text
    soup = BeautifulSoup(content, 'html.parser')

    # For different job sites, use different selectors to get more relevant content
    text = ""

    if "jobs.ac.uk" in url:
        # For jobs.ac.uk, get main content areas
        main_content = soup.find('main') or soup.find('div', class_='main-content') or soup.find('article')
        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()
    elif "careers.hsbc" in url:
        # For HSBC careers, try to get job-specific content
        # Look for main content containers, job details sections
        job_content = (soup.find('div', class_='jobDescription') or
                      soup.find('div', class_='job-detail') or
                      soup.find('div', class_='job-content') or
                      soup.find('div', attrs={'data-testid': 'job-description'}) or
                      soup.find('div', id='jobDescription') or
                      soup.find('section', class_='job') or
                      soup.find('main') or
                      soup.find('article'))

        if job_content:
            # Remove cookie consent banners and other non-job content
            for element in job_content.find_all(['div', 'section'], class_=lambda x: x and ('cookie' in x.lower() or 'consent' in x.lower() or 'banner' in x.lower())):
                element.decompose()

            text = job_content.get_text()
        else:
            # If no specific job content found, get all text but try to filter out cookie stuff
            text = soup.get_text()
    else:
        # For other sites, use general approach
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()

    # Clean up the text by removing excessive whitespace and redundant phrases
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.isspace():
            # Skip lines that are obviously cookie-related
            if not any(skip_phrase in line.lower() for skip_phrase in ['cookie', 'cookies', 'accept', 'consent', 'preferences', 'privacy', 'terms']):
                cleaned_lines.append(line)

    # Join the cleaned lines and split into chunks
    cleaned_text = '\n'.join(cleaned_lines)
    return [chunk for chunk in cleaned_text.split("\n\n") if chunk.strip()]

def split_into_chunks(doc_file: str) -> List[str]:
    """Reads a document and splits it into chunks based on double newlines."""
    with open(doc_file, 'r', encoding='utf-8') as file:
        content = file.read()
    return [chunk for chunk in content.split("\n\n") if chunk.strip()]