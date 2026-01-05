from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import get_all_jobs
from auth import User, get_user, get_user_by_email, create_user, init_users_table
import os
import requests
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL, WECHAT_CLIENT_ID, WECHAT_CLIENT_SECRET, WECHAT_AUTHORIZE_URL, WECHAT_TOKEN_URL, WECHAT_USER_INFO_URL
import sqlite3
import socket
import threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev_secret_key"  # Change this for production

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Thread lock for database access
db_lock = threading.Lock()

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url=GOOGLE_DISCOVERY_URL,
    client_kwargs={
        "scope": "openid email profile"
    },
)

# WeChat OAuth registration
wechat = oauth.register(
    name="wechat",
    client_id=WECHAT_CLIENT_ID,
    client_secret=WECHAT_CLIENT_SECRET,
    access_token_url=WECHAT_TOKEN_URL,
    authorize_url=WECHAT_AUTHORIZE_URL,
    api_base_url="https://api.weixin.qq.com/sns",
    client_kwargs={
        "scope": "snsapi_login"  # WeChat scope for login
    },
)

def save_visitor(ip_address, user_agent=None):
    """Save visitor information to the database."""
    user_id = None
    try:
        # Check if we're in a request context and current_user is available
        from flask import has_request_context
        if has_request_context():
            from flask_login import current_user
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
    except (RuntimeError, AttributeError):
        # Not in a Flask request context or current_user not available, treat as guest
        pass

    with db_lock:
        conn = sqlite3.connect('jobs.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO visitors (ip_address, timestamp, user_agent, user_id)
            VALUES (?, ?, ?, ?)
        ''', (ip_address, datetime.now().isoformat(), user_agent, user_id))
        conn.commit()
        conn.close()

def get_visitors(limit=100):
    """Get the list of visitors from the database."""
    with db_lock:
        conn = sqlite3.connect('jobs.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.ip_address, v.timestamp, v.user_agent, u.name
            FROM visitors v
            LEFT JOIN users u ON v.user_id = u.id
            ORDER BY v.timestamp DESC
            LIMIT ?
        ''', (limit,))
        visitors = cursor.fetchall()
        conn.close()
        return visitors

def get_ip_location(ip_address):
    """Get location and coordinates for an IP address."""
    try:
        # Try to get reverse DNS
        reverse_dns = socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror):
        reverse_dns = "N/A"

    # Try to get location info using a free API
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=2)
        if response.status_code == 200:
            data = response.json()
            country = data.get('country', 'N/A')
            city = data.get('city', 'N/A')
            region = data.get('regionName', 'N/A')
            lat = data.get('lat', None)
            lon = data.get('lon', None)
            location = f"{city}, {region}, {country}"

            # Return location, reverse_dns, and coordinates for weather API
            return location, reverse_dns, lat, lon
        else:
            return "Location unavailable", reverse_dns, None, None
    except:
        return "Location unavailable", reverse_dns, None, None

def get_weather_info(lat, lon):
    """Get weather information for given coordinates."""
    import os
    api_key = os.getenv('OPENWEATHER_API_KEY')

    if not api_key or not lat or not lon:
        return "Weather unavailable"

    try:
        # Call OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=3)

        if response.status_code == 200:
            data = response.json()
            temperature = round(data['main']['temp'])
            description = data['weather'][0]['description']
            humidity = data['main']['humidity']
            weather_info = f"{temperature}°C, {description}, Humidity: {humidity}%"
            return weather_info
        else:
            return "Weather unavailable"
    except Exception as e:
        print(f"Weather API error: {e}")
        return "Weather unavailable"

@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

# Initialize users table
init_users_table()

def init_cv_uploads_table():
    """Initialize the CV uploads table if it doesn't exist."""
    conn = sqlite3.connect("jobs.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cv_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

def init_job_applications_table():
    """Initialize the job applications table if it doesn't exist."""
    conn = sqlite3.connect("jobs.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            job_title TEXT,
            job_organization TEXT,
            job_location TEXT,
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Applied',
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (job_id) REFERENCES job_postings (id)
        )
    """)
    conn.commit()
    conn.close()

# Initialize CV uploads and job applications tables
init_cv_uploads_table()
init_job_applications_table()

# Make current_user available in all templates
@app.template_filter('truncate_words')
def truncate_words(text, num_words=50):
    """Truncate text to specified number of words."""
    if not text:
        return ""

    words = text.split()
    if len(words) <= num_words:
        return text

    return ' '.join(words[:num_words]) + '...'

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Cache for geocoding results
geocode_cache = {}

def parse_date(date_str):
    """Parse date string from database format"""
    if not date_str or date_str == "None":
        return None

    # Clean up the date string by removing field labels
    date_str = date_str.replace("Placed On:", "").replace("Closes:", "").strip()

    # Try different date formats
    formats = [
        "%dth %B %Y",  # 22nd December 2025
        "%dst %B %Y",  # 1st January 2026
        "%dnd %B %Y",  # 2nd January 2026
        "%drd %B %Y",  # 3rd January 2026
        "%d %B %Y",    # 1 January 2026 (fallback)
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None

def filter_jobs_by_date(jobs, days=None):
    """Filter jobs by date range (last N days)"""
    if not days:
        return jobs

    try:
        days = int(days)
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_jobs = []

        for job in jobs:
            # Try placed_on date first, then closes date
            job_date = parse_date(job.get("placed_on")) or parse_date(job.get("closes"))

            if job_date and job_date >= cutoff_date:
                filtered_jobs.append(job)

        return filtered_jobs
    except (ValueError, TypeError):
        return jobs

def geocode_location(location):
    """Convert location name to coordinates using Nominatim API"""
    if not location:
        return None

    # Check cache first
    if location in geocode_cache:
        return geocode_cache[location]

    try:
        # Clean up location string
        clean_location = location.replace(", Hybrid", "").strip()

        # Determine if this is likely a UK location or international
        # If it contains obvious international indicators, don't append ", UK"
        is_international = any(indicator in clean_location.lower() for indicator in
                              ['cn', 'china', 'guangzhou', 'beijing', 'shanghai', 'hk', 'hong kong',
                               'usa', 'us', 'united states', 'canada', 'australia', 'germany',
                               'france', 'italy', 'spain', 'japan', 'korea', 'india', 'brazil'])

        # Use Nominatim API (OpenStreetMap)
        url = "https://nominatim.openstreetmap.org/search"
        if is_international:
            params = {
                "q": clean_location,
                "format": "json",
                "limit": 1
            }
        else:
            params = {
                "q": f"{clean_location}, UK",  # Assume UK locations for jobs.ac.uk
                "format": "json",
                "limit": 1
            }
        headers = {"User-Agent": "RAG-Job-Search/1.0"}

        response = requests.get(url, params=params, headers=headers)
        data = response.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            result = {"lat": lat, "lon": lon, "display_name": data[0]["display_name"]}
            geocode_cache[location] = result
            return result

    except Exception as e:
        print(f"Geocoding error for {location}: {e}")

    # Fallback coordinates for common UK cities
    fallbacks = {
        "London": {"lat": 51.5074, "lon": -0.1278, "display_name": "London, UK"},
        "Cambridge": {"lat": 52.2053, "lon": 0.1218, "display_name": "Cambridge, UK"},
        "Edinburgh": {"lat": 55.9533, "lon": -3.1883, "display_name": "Edinburgh, UK"},
        "Southampton": {"lat": 50.9097, "lon": -1.4044, "display_name": "Southampton, UK"},
        "Plymouth": {"lat": 50.3755, "lon": -4.1427, "display_name": "Plymouth, UK"}
    }

    # Also add some international fallbacks
    international_fallbacks = {
        "Guangzhou": {"lat": 23.1291, "lon": 113.2644, "display_name": "Guangzhou, China"},
        "Beijing": {"lat": 39.9042, "lon": 116.4074, "display_name": "Beijing, China"},
        "Shanghai": {"lat": 31.2304, "lon": 121.4737, "display_name": "Shanghai, China"},
        "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "display_name": "Hong Kong, China"},
        "New York": {"lat": 40.7128, "lon": -74.0060, "display_name": "New York, USA"},
        "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "display_name": "Los Angeles, USA"},
        "Tokyo": {"lat": 35.6762, "lon": 139.6503, "display_name": "Tokyo, Japan"},
        "Paris": {"lat": 48.8566, "lon": 2.3522, "display_name": "Paris, France"},
        "Berlin": {"lat": 52.5200, "lon": 13.4050, "display_name": "Berlin, Germany"},
        "Sydney": {"lat": -33.8688, "lon": 151.2093, "display_name": "Sydney, Australia"}
    }

    # Try to match against both UK and international fallbacks
    result = fallbacks.get(clean_location)
    if result:
        geocode_cache[location] = result
        return result

    # Try to find a match in the international fallbacks
    # Look for partial matches in the location string
    for city, coords in international_fallbacks.items():
        if city.lower() in clean_location.lower():
            geocode_cache[location] = coords
            return coords

    return result

@app.route("/")
def index():
    """Main page displaying all jobs"""
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    print(f"Home page accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    jobs = get_all_jobs()
    days_filter = request.args.get("days")

    if days_filter:
        jobs = filter_jobs_by_date(jobs, days_filter)

    return render_template("index.html", jobs=jobs, days_filter=days_filter)

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    """Display detailed view of a specific job"""
    jobs = get_all_jobs()
    job = next((job for job in jobs if job["id"] == job_id), None)
    if job is None:
        return "Job not found", 404
    return render_template("job_detail.html", job=job)

@app.route("/map")
def map_view():
    """Display jobs on an interactive map"""
    jobs = get_all_jobs()
    days_filter = request.args.get("days")

    if days_filter:
        jobs = filter_jobs_by_date(jobs, days_filter)

    # Add coordinates to jobs
    jobs_with_coords = []
    for job in jobs:
        coords = geocode_location(job["location"])
        if coords:
            job_with_coords = dict(job)
            job_with_coords.update(coords)
            jobs_with_coords.append(job_with_coords)

    return render_template("map.html", jobs=jobs_with_coords, days_filter=days_filter)

@app.route("/search")
def search():
    """Search jobs by title, organization, or location"""
    query = request.args.get("q", "").lower()
    days_filter = request.args.get("days")

    if not query:
        return redirect(url_for("index", days=days_filter))

    jobs = get_all_jobs()

    # Apply date filter first
    if days_filter:
        jobs = filter_jobs_by_date(jobs, days_filter)

    # Then apply search filter
    filtered_jobs = []
    for job in jobs:
        # Search in title, organization, location, and description
        searchable_text = f"{job.get("title", "")} {job.get("organization", "")} {job.get("location", "")} {job.get("description", "")}".lower()
        if query in searchable_text:
            filtered_jobs.append(job)

    return render_template("index.html", jobs=filtered_jobs, search_query=query, days_filter=days_filter)

@app.route("/login")
def login():
    """Show login options."""
    return render_template("login.html")

@app.route("/login/google")
def login_google():
    """Redirect to Google for authentication."""
    redirect_uri = url_for("callback", _external=True)
    print(f"Initiating Google OAuth with redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route("/login/wechat")
def login_wechat():
    """Redirect to WeChat for authentication."""
    redirect_uri = url_for("wechat_callback", _external=True)
    print(f"Initiating WeChat OAuth with redirect URI: {redirect_uri}")
    # For WeChat, we need to use a different approach since Authlib doesn't fully support WeChat OAuth
    # We'll implement a custom flow
    import urllib.parse
    params = {
        'appid': WECHAT_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'snsapi_login',
        'state': 'wechat_auth'  # Add a state parameter for security
    }
    url = f"{WECHAT_AUTHORIZE_URL}?" + urllib.parse.urlencode(params) + "#wechat_redirect"
    return redirect(url)

@app.route("/callback")
def callback():
    """Handle the Google OAuth callback."""
    try:
        # Debug logging
        print("Starting OAuth callback...")

        token = google.authorize_access_token()
        print(f"Token received: {"yes" if token else "no"}")

        # Get user info from Google"s userinfo endpoint
        user_info = token.get("userinfo")
        if not user_info:
            print("Userinfo not in token, fetching from Google...")
            # If userinfo is not in the token, fetch it using the access token
            resp = google.get("userinfo")
            user_info = resp.json()
            print(f"Userinfo fetched: {"yes" if user_info else "no"}")
        else:
            print("Userinfo found in token")

        print(f"User info keys: {list(user_info.keys()) if user_info else "None"}")

        if user_info and user_info.get("email"):
            print(f"User email: {user_info["email"]}")
            user = get_user_by_email(user_info["email"])
            if not user:
                print("Creating new user...")
                user = create_user(
                    email=user_info["email"],
                    name=user_info.get("name", user_info.get("email", "Unknown")),
                    profile_pic=user_info.get("picture"),
                    provider='google',
                    provider_user_id=user_info.get('sub')  # Google's user ID
                )
            else:
                print("Updating existing user...")
                # Update user info if it exists
                import sqlite3
                conn = sqlite3.connect("jobs.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET name=?, profile_pic=? WHERE email=?",
                              (user_info.get("name", user_info.get("email", "Unknown")),
                               user_info.get("picture"),
                               user_info["email"]))
                conn.commit()
                conn.close()
                # Update the user object with new info
                user.name = user_info.get("name", user_info.get("email", "Unknown"))
                user.profile_pic = user_info.get("picture")

            login_user(user)
            print("User logged in successfully, redirecting...")
            return redirect(url_for("index"))
        else:
            print(f"Authentication failed - no user info received. User info: {user_info}")
            return "Authentication failed - no user info received.", 400
    except Exception as e:
        print(f"Error during OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        return "Authentication failed.", 400

@app.route("/wechat_callback")
def wechat_callback():
    """Handle the WeChat OAuth callback."""
    try:
        # Get the authorization code from the callback
        code = request.args.get('code')
        if not code:
            return "Authorization code not received.", 400

        # Exchange the code for an access token
        token_params = {
            'appid': WECHAT_CLIENT_ID,
            'secret': WECHAT_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }

        token_response = requests.get(WECHAT_TOKEN_URL, params=token_params)
        token_data = token_response.json()

        if 'access_token' not in token_data:
            print(f"WeChat token exchange failed: {token_data}")
            return "WeChat token exchange failed.", 400

        access_token = token_data['access_token']
        openid = token_data['openid']  # WeChat user ID

        # Get user info using access token and openid
        user_info_params = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN'
        }

        user_info_response = requests.get(WECHAT_USER_INFO_URL, params=user_info_params)
        user_info = user_info_response.json()

        if 'nickname' not in user_info:
            print(f"WeChat user info retrieval failed: {user_info}")
            return "WeChat user info retrieval failed.", 400

        # Check if user already exists by provider and provider_user_id
        user = get_user_by_provider('wechat', openid)
        if not user:
            # Create new user
            user = create_user(
                email=None,  # WeChat might not provide email
                name=user_info.get('nickname', 'WeChat User'),
                profile_pic=user_info.get('headimgurl', ''),
                provider='wechat',
                provider_user_id=openid
            )
        else:
            # Update existing user info
            import sqlite3
            conn = sqlite3.connect("jobs.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET name=?, profile_pic=? WHERE provider=? AND provider_user_id=?",
                          (user_info.get('nickname', 'WeChat User'),
                           user_info.get('headimgurl', ''),
                           'wechat',
                           openid))
            conn.commit()
            conn.close()
            # Update the user object with new info
            user.name = user_info.get('nickname', 'WeChat User')
            user.profile_pic = user_info.get('headimgurl', '')

        login_user(user)
        print("WeChat user logged in successfully, redirecting...")
        return redirect(url_for("index"))
    except Exception as e:
        print(f"Error during WeChat OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        return "WeChat authentication failed.", 400

def get_user_cvs(user_id):
    """Get all CVs uploaded by a specific user."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, filename, filepath, upload_date FROM cv_uploads WHERE user_id = ? ORDER BY upload_date DESC",
        (user_id,)
    )
    cv_records = cursor.fetchall()
    conn.close()

    # Convert to list of dictionaries for easier template use
    cvs = []
    for record in cv_records:
        cvs.append({
            'id': record[0],
            'filename': record[1],
            'filepath': record[2],
            'upload_date': record[3]
        })

    return cvs

def get_user_applications(user_id):
    """Get all job applications for a specific user."""
    conn = sqlite3.connect("jobs.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ja.id, ja.job_id, ja.job_title, ja.job_organization,
               ja.job_location, ja.application_date, ja.status,
               jp.title as job_title_db, jp.organization as job_organization_db,
               jp.location as job_location_db
        FROM job_applications ja
        LEFT JOIN job_postings jp ON ja.job_id = jp.id
        WHERE ja.user_id = ?
        ORDER BY ja.application_date DESC
    """, (user_id,))
    application_records = cursor.fetchall()
    conn.close()

    # Convert to list of dictionaries for easier template use
    applications = []
    for record in application_records:
        # Use the application record values first, fallback to DB values
        job_title = record[2] or record[7] or 'Untitled Position'
        job_organization = record[3] or record[8] or 'Unknown'
        job_location = record[4] or record[9] or 'Unknown'

        applications.append({
            'id': record[0],
            'job_id': record[1],
            'job_title': job_title,
            'job_organization': job_organization,
            'job_location': job_location,
            'application_date': record[5],
            'status': record[6]
        })

    return applications

def allowed_file(filename):
    """Check if the uploaded file is allowed."""
    allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

@app.route("/my_cvs")
@login_required
def my_cvs():
    """Display user's uploaded CVs."""
    user_cvs = get_user_cvs(current_user.id)
    return render_template("my_cvs.html", cvs=user_cvs, user=current_user)

@app.route("/profile")
@login_required
def profile():
    """Display user's profile with CVs and job applications."""
    user_cvs = get_user_cvs(current_user.id)
    user_applications = get_user_applications(current_user.id)
    return render_template("profile.html", user=current_user, cvs=user_cvs, applications=user_applications)

@app.route("/upload_cv", methods=["GET", "POST"])
@login_required
def upload_cv():
    """Allow logged-in users to upload their CV."""
    user_cvs = get_user_cvs(current_user.id)

    if request.method == "POST":
        # Check if file was submitted
        if "cv_file" not in request.files:
            flash("No file selected", "error")
            return redirect(request.url)

        file = request.files["cv_file"]

        # Check if file was actually selected
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(request.url)

        # Check if file is allowed
        if file and allowed_file(file.filename):
            import uuid
            from werkzeug.utils import secure_filename

            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(app.root_path, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            # Generate a unique filename to avoid conflicts
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            filepath = os.path.join(upload_dir, unique_filename)

            # Save the file
            file.save(filepath)

            # Store file info in the database
            conn = sqlite3.connect("jobs.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cv_uploads (user_id, filename, filepath) VALUES (?, ?, ?)",
                (current_user.id, secure_filename(file.filename), filepath)
            )
            conn.commit()
            conn.close()

            flash("CV uploaded successfully!", "success")
            return redirect(url_for("upload_cv"))  # Redirect back to upload page to see the new CV
        else:
            flash("Invalid file type. Please upload a PDF, DOC, DOCX, TXT, or RTF file.", "error")
            return redirect(request.url)

    # GET request - show upload form
    return render_template("upload_cv.html", user=current_user, cvs=user_cvs)

@app.route("/logout")
def logout():
    """Logout the current user."""
    logout_user()
    return redirect(url_for("index"))

@app.route('/visitors')
def visitor_history():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    print(f"Visitor history endpoint accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    visitors = get_visitors()

    # Create HTML response
    html = '''
    <h1>访问者历史</h1>
    <table border="1" style="border-collapse: collapse; width: 100%; font-size: 14px;">
        <thead>
            <tr>
                <th>IP地址</th>
                <th>用户名</th>
                <th>位置</th>
                <th>反向DNS</th>
                <th>天气</th>
                <th>时间戳</th>
                <th>用户代理</th>
            </tr>
        </thead>
        <tbody>
    '''

    for visitor in visitors:
        ip, timestamp, user_agent, username = visitor
        user_agent_display = user_agent if user_agent else "N/A"
        username_display = username if username else "访客"

        # Get location, reverse DNS, and coordinates
        location, reverse_dns, lat, lon = get_ip_location(ip)

        # Get weather info if coordinates are available
        weather_info = "Weather unavailable"
        if lat and lon:
            weather_info = get_weather_info(lat, lon)

        html += f'''
            <tr>
                <td>{ip}</td>
                <td>{username_display}</td>
                <td>{location}</td>
                <td>{reverse_dns}</td>
                <td>{weather_info}</td>
                <td>{timestamp}</td>
                <td>{user_agent_display}</td>
            </tr>
        '''

    html += '''
        </tbody>
    </table>
    <br>
    <a href="/">返回主页</a>
    '''

    return html

if __name__ == "__main__":
    # Run with SSL context for HTTPS
    import ssl
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain('ssl_certificates/cert.pem', 'ssl_certificates/key.pem')
    app.run(debug=True, host="0.0.0.0", port=5000, ssl_context=context)
