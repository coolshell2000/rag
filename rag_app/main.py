import os
from config import GEMINI_API_KEY
from database import create_job_database, parse_job_chunks, save_job_to_db
from scraper import split_into_chunks, split_into_chunks_from_url
from rag import embed_chunk, save_embeddings, retrieve, rerank, generate

def main():
    # 1. Data Preparation
    doc_path = "story_chinese.md"
    if not os.path.exists(doc_path):
        print(f"Error: {doc_path} not found.")
        return

    print("Splitting document into chunks...")
    chunks = split_into_chunks(doc_path)
    
    # 2. Embedding Generation
    print("Generating embeddings...")
    embeddings = [embed_chunk(chunk) for chunk in chunks]
    
    # 3. Vector Storage
    print("Saving to vector database...")
    save_embeddings(chunks, embeddings)
    
    # 4. Retrieval & Reranking
    query = "有哪些人物, 冒险中他们分别使用了哪些秘密道具？ 找到了啥宝藏?"
    print(f"Querying: {query}")
    
    retrieved_chunks = retrieve(query, top_k=5)
    reranked_chunks = rerank(query, retrieved_chunks, top_k=3)
    
    # 5. Answer Generation
    print("Generating answer...")
    answer = generate(query, reranked_chunks)
    
    print("\n--- Final Answer ---")
    print(answer)

def scrape_and_store_job(url: str):
    """Scrapes a job posting from URL and stores it in the database."""
    print(f"Scraping job from {url}...")
    chunks = split_into_chunks_from_url(url)
    job_data = parse_job_chunks(chunks)
    create_job_database()
    save_job_to_db(url, job_data)
    print("Job stored in database.")

def print_all_jobs(db_path: str = "jobs.db"):
    """Prints all jobs stored in the database in a formatted way."""
    from database import get_all_jobs

    jobs = get_all_jobs(db_path)

    if not jobs:
        print("No jobs found in the database.")
        return

    print(f"\n{'='*80}")
    print(f"JOBS DATABASE - {len(jobs)} job(s) found")
    print(f"{'='*80}")

    for i, job in enumerate(jobs, 1):
        print(f"\n{'─'*60}")
        print(f"Job #{i} (ID: {job['id']})")
        print(f"{'─'*60}")

        # Basic job info
        if job['title']:
            print(f"Title: {job['title']}")
        if job['organization']:
            print(f"Organization: {job['organization']}")
        if job['location']:
            print(f"Location: {job['location']}")

        # Salary info
        if job['salary_min'] or job['salary_max']:
            salary_str = ""
            if job['salary_min']:
                salary_str += f"£{job['salary_min']:,}"
            if job['salary_max']:
                if salary_str:
                    salary_str += f" - £{job['salary_max']:,}"
                else:
                    salary_str += f"£{job['salary_max']:,}"
            print(f"Salary: {salary_str}")

        # Employment details
        if job['hours']:
            print(f"Hours: {job['hours']}")
        if job['contract_type']:
            print(f"Contract Type: {job['contract_type']}")

        # Dates
        if job['placed_on']:
            print(f"Placed On: {job['placed_on']}")
        if job['closes']:
            print(f"Closes: {job['closes']}")

        # Reference
        if job['job_ref']:
            print(f"Job Reference: {job['job_ref']}")

        # Description (truncated)
        if job['description']:
            desc = job['description'][:200] + "..." if len(job['description']) > 200 else job['description']
            print(f"Description: {desc}")

        # Benefits
        if job['benefits']:
            print(f"Benefits: {job['benefits']}")

        # URL
        if job['url']:
            print(f"URL: {job['url']}")

    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()
