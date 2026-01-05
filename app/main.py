import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
import sqlite3
import threading


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread lock for database access
db_lock = threading.Lock()

def init_db():
    """Initialize the database and create the visitors table if it doesn't exist."""
    with db_lock:
        conn = sqlite3.connect('visitors.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_agent TEXT
            )
        ''')
        conn.commit()
        conn.close()

def save_visitor(ip_address, user_agent=None):
    """Save visitor information to the database."""
    with db_lock:
        conn = sqlite3.connect('visitors.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO visitors (ip_address, timestamp, user_agent)
            VALUES (?, ?, ?)
        ''', (ip_address, datetime.now().isoformat(), user_agent))
        conn.commit()
        conn.close()

def get_visitors(limit=100):
    """Get the list of visitors from the database."""
    with db_lock:
        conn = sqlite3.connect('visitors.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ip_address, timestamp, user_agent
            FROM visitors
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        visitors = cursor.fetchall()
        conn.close()
        return visitors

# Initialize database on startup
init_db()

# Add error handling
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    logger.error(f"HTTP error occurred: {e.code} - {e.description}")
    response = {
        "error": {
            "code": e.code,
            "message": e.description
        }
    }
    return jsonify(response), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON for server errors."""
    logger.error(f"Unexpected error occurred: {str(e)}")
    response = {
        "error": {
            "code": 500,
            "message": "Internal server error"
        }
    }
    return jsonify(response), 500

@app.route('/')
def home():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    logger.info(f"Home page accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    return '''
    <h1>欢迎来到TAOTAO应用!</h1>
    <p>这是一个可部署的Flask应用示例。</p>
    <a href="/api/status">查看API状态</a> |
    <a href="/health">健康检查</a> |
    <a href="/visitors">访问者历史</a>
    '''

@app.route('/api/status')
def api_status():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    logger.info(f"API status endpoint accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    return jsonify({
        'status': 'success',
        'message': 'Flask API is running!',
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })

@app.route('/health')
def health_check():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    logger.info(f"Health check endpoint accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    return jsonify({'status': 'healthy'}), 200

# Additional endpoint for readiness check
@app.route('/ready')
def readiness_check():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    logger.info(f"Readiness check endpoint accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    return jsonify({'status': 'ready'}), 200

# New endpoint to display visitor history
@app.route('/visitors')
def visitor_history():
    # Get the real IP address (considering proxies)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    user_agent = request.headers.get('User-Agent')
    logger.info(f"Visitor history endpoint accessed by IP: {ip_address}")
    save_visitor(ip_address, user_agent)

    visitors = get_visitors()

    # Create HTML response
    html = '''
    <h1>访问者历史</h1>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr>
                <th>IP地址</th>
                <th>时间戳</th>
                <th>用户代理</th>
            </tr>
        </thead>
        <tbody>
    '''

    for visitor in visitors:
        ip, timestamp, user_agent = visitor
        user_agent_display = user_agent if user_agent else "N/A"
        html += f'''
            <tr>
                <td>{ip}</td>
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

