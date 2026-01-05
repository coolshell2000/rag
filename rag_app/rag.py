import chromadb
from typing import List
from sentence_transformers import SentenceTransformer, CrossEncoder
from google import genai
from config import EMBEDDING_MODEL_NAME, CROSS_ENCODER_MODEL_NAME, CHROMADB_COLLECTION_NAME, GEMINI_MODEL, GEMINI_API_KEY

# Initialize models and clients
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL_NAME)
chromadb_client = chromadb.EphemeralClient()
chromadb_collection = chromadb_client.get_or_create_collection(name=CHROMADB_COLLECTION_NAME)
google_client = genai.Client()

def embed_chunk(chunk: str) -> List[float]:
    """Generates a normalized embedding for a given text chunk."""
    embedding = embedding_model.encode(chunk, normalize_embeddings=True)
    return embedding.tolist()

def save_embeddings(chunks: List[str], embeddings: List[List[float]]) -> None:
    """Stores chunks and their corresponding embeddings into ChromaDB."""
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chromadb_collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(i)]
        )

def retrieve(query: str, top_k: int) -> List[str]:
    """Retrieves the most similar chunks from the vector database."""
    query_embedding = embed_chunk(query)
    results = chromadb_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results['documents'][0]

def rerank(query: str, retrieved_chunks: List[str], top_k: int) -> List[str]:
    """Refines the retrieved results using a Cross-Encoder for better accuracy."""
    if not retrieved_chunks:
        return []
    pairs = [(query, chunk) for chunk in retrieved_chunks]
    scores = cross_encoder.predict(pairs)
    scored_chunks = list(zip(retrieved_chunks, scores))
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in scored_chunks][:top_k]

def generate(query: str, chunks: List[str]) -> str:
    """Generates a final response using an LLM based on the provided context chunks."""
    prompt = f"""你是一位知识助手，请根据用户的问题和下列片段生成准确的回答。

用户问题: {query}

相关片段:
{"\n\n".join(chunks)}

请基于上述内容作答，不要编造信息。"""

    print(f"--- Prompt Sent to LLM ---\n{prompt}\n\n---\n")

    response = google_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return response.text

def extract_job_info(chunks: List[str]) -> dict:
    """
    Extracts structured job information from scraped content using RAG.

    Args:
        chunks: List of text chunks from the job posting

    Returns:
        Dictionary containing structured job information
    """
    if not chunks:
        return {}

    # Create a comprehensive prompt for job information extraction
    prompt = f"""You are an expert at extracting job information from job postings. Please analyze the following job posting content and extract the key information into a structured format.

Job Posting Content:
{"\n\n".join(chunks)}

Please extract the following information and format your response as a JSON-like structure:
- title: The job title
- organization: The organization/company name
- location: Where the job is located
- salary_min: Minimum salary (just the number, no currency symbols)
- salary_max: Maximum salary (just the number, no currency symbols)
- hours: Full time, part time, etc.
- contract_type: Permanent, contract, temporary, etc.
- placed_on: When the job was posted
- closes: When applications close
- job_ref: Job reference number
- description: A brief description of the role (2-3 sentences)
- benefits: Key benefits mentioned

If any information is not available, use null or empty string. Format your response as a valid JSON object.

Example format:
{{
    "title": "Research Fellow",
    "organization": "University of Cambridge",
    "location": "Cambridge",
    "salary_min": 35000,
    "salary_max": 45000,
    "hours": "Full Time",
    "contract_type": "Fixed Term",
    "placed_on": "1st January 2024",
    "closes": "31st January 2024",
    "job_ref": "ABC123",
    "description": "This is a research position...",
    "benefits": "35 days holiday, pension scheme"
}}

Extract only the information that is explicitly mentioned in the job posting."""

    print(f"--- Job Extraction Prompt ---\n{prompt}\n\n---\n")

    try:
        response = google_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        # Parse the JSON response
        import json
        import re

        # Extract JSON from the response (LLM might add extra text)
        response_text = response.text.strip()
        # Look for JSON object in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                job_data = json.loads(json_str)
                return job_data
            except json.JSONDecodeError:
                print(f"Failed to parse JSON response: {json_str}")
                return {}
        else:
            print(f"No JSON found in response: {response_text}")
            return {}

    except Exception as e:
        print(f"Error extracting job info: {e}")
        return {}