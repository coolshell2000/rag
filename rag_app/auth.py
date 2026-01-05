from flask_login import UserMixin
from database import get_all_jobs
import sqlite3
import os

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id_, email, name, profile_pic):
        self.id = id_
        self.email = email or ''  # Ensure email is never None
        self.name = name
        self.profile_pic = profile_pic

def get_user(user_id):
    """Retrieve a user from the database by ID."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, profile_pic FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def get_user_by_email(email):
    """Retrieve a user from the database by email."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, profile_pic FROM users WHERE email = ?", (email,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def get_user_by_provider(provider, provider_user_id):
    """Retrieve a user from the database by provider and provider_user_id."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, profile_pic FROM users WHERE provider = ? AND provider_user_id = ?",
                   (provider, provider_user_id))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def create_user(email, name, profile_pic, provider='local', provider_user_id=None):
    """Create a new user in the database."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, name, profile_pic, provider, provider_user_id) VALUES (?, ?, ?, ?, ?)",
                   (email, name, profile_pic, provider, provider_user_id))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return User(user_id, email or '', name, profile_pic)

def init_users_table():
    """Initialize the users table if it doesn't exist by ensuring job database is created."""
    from database import create_job_database
    create_job_database()  # This will also create the users table