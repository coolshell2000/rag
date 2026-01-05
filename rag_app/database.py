import sqlite3
from typing import Dict, Any

# SQLite Database Schema for Job Postings
JOB_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    organization TEXT,
    location TEXT,
    salary_min REAL,
    salary_max REAL,
    hours TEXT,
    contract_type TEXT,
    placed_on TEXT,
    closes TEXT,
    job_ref TEXT,
    description TEXT,
    benefits TEXT
);
"""

def create_job_database(db_path: str = "jobs.db"):
    """Creates the SQLite database and job_postings table."""
    conn = sqlite3.connect(db_path)
    conn.execute(JOB_DB_SCHEMA)
    # Also create the users table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT NOT NULL,
            profile_pic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            provider TEXT DEFAULT 'local',  -- 'local', 'google', 'wechat'
            provider_user_id TEXT,          -- Store provider-specific user ID
            UNIQUE(provider, provider_user_id) -- Ensure unique users per provider
        )
    """)
    # Create the visitors table for tracking visitor history
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_agent TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

def parse_job_chunks(chunks: list[str]) -> Dict[str, Any]:
    """Parses the list of chunks to extract job details into a dictionary."""
    job_data = {}
    i = 0
    while i < len(chunks):
        chunk = chunks[i].strip()
        if not chunk:
            i += 1
            continue
            
        # Look for job title (first substantial chunk that contains " at " or looks like a job title)
        if not job_data.get('title') and len(chunk) > 5 and not chunk.startswith(('Location:', 'Salary:', 'Hours:', 'Contract Type:', 'Placed On:', 'Closes:', 'Job Ref:', 'Skip to', 'Find a', 'Career', 'Jobs by', 'Advertise', 'Your Account', 'Back to', 'Copyright', '£')):
            # Check if it contains " at " (title at organization)
            if " at " in chunk:
                parts = chunk.split(" at ", 1)
                job_data['title'] = parts[0].strip()
                job_data['organization'] = parts[1].strip()
            else:
                # Check if this looks like a job title (not a label, not too long for a title)
                if len(chunk) < 100 and not any(keyword in chunk.lower() for keyword in ['you interested', 'holiday', 'days']):
                    job_data['title'] = chunk
        elif chunk == "Location:" and i + 1 < len(chunks):
            job_data['location'] = chunks[i + 1].strip()
            i += 1  # Skip next chunk as it's been processed
        elif "Location:" in chunk and "GD," in chunk and "CN" in chunk:
            # Handle international format like "Location: Guangzhou, GD, CN, 510620"
            parts = chunk.split("Location:")
            if len(parts) > 1:
                location_part = parts[1].strip()
                job_data['location'] = location_part
        elif "Guangzhou" in chunk and "GD" in chunk and "CN" in chunk:
            # Direct match for Guangzhou location format
            job_data['location'] = chunk.replace("Associate Director, Management Specialist Job Details | HSBC Global Services Limited", "").strip()
            if job_data['location'].startswith("Skip to main content"):
                job_data['location'] = "Guangzhou, GD, CN, 510620"
        elif chunk == "Salary:" and i + 1 < len(chunks):
            salary_text = chunks[i + 1].replace("£", "").replace(",", "").strip()
            if " to " in salary_text:
                min_sal, max_sal = salary_text.split(" to ")
                try:
                    job_data['salary_min'] = float(min_sal)
                    job_data['salary_max'] = float(max_sal)
                except ValueError:
                    pass  # Skip if not valid numbers
            i += 1  # Skip next chunk as it's been processed
        elif chunk == "Hours:" and i + 1 < len(chunks):
            job_data['hours'] = chunks[i + 1].strip()
            i += 1
        elif chunk == "Contract Type:" and i + 1 < len(chunks):
            job_data['contract_type'] = chunks[i + 1].strip()
            i += 1
        elif chunk == "Placed On:" and i + 1 < len(chunks):
            job_data['placed_on'] = chunks[i + 1].strip()
            i += 1
        elif chunk == "Closes:" and i + 1 < len(chunks):
            job_data['closes'] = chunks[i + 1].strip()
            i += 1
        elif chunk == "Job Ref:" and i + 1 < len(chunks):
            job_data['job_ref'] = chunks[i + 1].strip()
            i += 1
        elif "holiday" in chunk.lower() or ("days" in chunk.lower() and "holiday" in chunk.lower()):
            job_data['benefits'] = chunk
        elif len(chunk) > 40 and not any(keyword in chunk for keyword in ['Location:', 'Salary:', 'Hours:', 'Contract Type:', 'Placed On:', 'Closes:', 'Job Ref:', 'Full Time', 'Part Time', 'Permanent', 'Contract', 'Temporary', 'VC', '£']):  # Likely description
            if 'description' not in job_data:
                job_data['description'] = chunk
        i += 1
    
    return job_data

def save_job_to_db(url: str, job_data: Dict[str, Any], db_path: str = "jobs.db"):
    """Saves the parsed job data to the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO job_postings
        (url, title, organization, location, salary_min, salary_max, hours, contract_type, placed_on, closes, job_ref, description, benefits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        url,
        job_data.get('title'),
        job_data.get('organization'),
        job_data.get('location'),
        job_data.get('salary_min'),
        job_data.get('salary_max'),
        job_data.get('hours'),
        job_data.get('contract_type'),
        job_data.get('placed_on'),
        job_data.get('closes'),
        job_data.get('job_ref'),
        job_data.get('description'),
        job_data.get('benefits')
    ))
    conn.commit()
    conn.close()

def get_all_jobs(db_path: str = "jobs.db") -> list[Dict[str, Any]]:
    """Retrieves all job postings from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings")
    rows = cursor.fetchall()
    conn.close()
    # Convert to dicts
    columns = ['id', 'url', 'title', 'organization', 'location', 'salary_min', 'salary_max', 'hours', 'contract_type', 'placed_on', 'closes', 'job_ref', 'description', 'benefits']
    return [dict(zip(columns, row)) for row in rows]