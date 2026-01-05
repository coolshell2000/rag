import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request, redirect, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.exceptions import HTTPException
import sqlite3
import threading
import requests


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')

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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth
oauth = OAuth(app)

from auth import User, init_users_table, get_user, create_user, get_user_by_provider, get_user_by_email
from config import SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL, WECHAT_CLIENT_ID, WECHAT_CLIENT_SECRET, WECHAT_AUTHORIZE_URL, WECHAT_TOKEN_URL, WECHAT_USER_INFO_URL

# Set secret key
app.secret_key = SECRET_KEY

# Google OAuth registration
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=GOOGLE_DISCOVERY_URL,
        client_kwargs={
            "scope": "openid email profile"
        },
    )
    print("Google OAuth configured")
else:
    print("Google OAuth not configured - missing environment variables")

# WeChat OAuth registration
if WECHAT_CLIENT_ID and WECHAT_CLIENT_SECRET:
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
    print("WeChat OAuth configured")
else:
    print("WeChat OAuth not configured - missing environment variables")

@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

# Initialize users table
init_users_table()

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
    <a href="/login">登录</a> |
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
@app.route('/login')
def login():
    """Show login options."""
    # Pass available login providers to the template
    available_providers = {
        'google': bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        'wechat': bool(WECHAT_CLIENT_ID and WECHAT_CLIENT_SECRET)
    }
    return render_template('login.html', providers=available_providers)

@app.route('/login/google')
def login_google():
    """Redirect to Google for authentication."""
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return "Google OAuth is not configured", 400

    redirect_uri = request.url_root + 'callback/google'
    return google.authorize_redirect(redirect_uri)

@app.route('/callback/google')
def google_callback():
    """Handle the Google OAuth callback."""
    try:
        if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
            return "Google OAuth is not configured", 400

        token = google.authorize_access_token()
        user_info = token.get("userinfo")

        if user_info and user_info.get("email"):
            user = get_user_by_email(user_info["email"])
            if not user:
                user = create_user(
                    email=user_info["email"],
                    name=user_info.get("name", user_info.get("email", "Unknown")),
                    profile_pic=user_info.get("picture"),
                    provider='google',
                    provider_user_id=user_info.get('sub')  # Google's user ID
                )
            else:
                # Update user info if it exists
                import sqlite3
                conn = sqlite3.connect('visitors.db')
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
            return redirect('/')

        return "Authentication failed - no user info received.", 400
    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}")
        return "Authentication failed.", 400

@app.route('/login/wechat')
def login_wechat():
    """Redirect to WeChat for authentication."""
    if not (WECHAT_CLIENT_ID and WECHAT_CLIENT_SECRET):
        return "WeChat OAuth is not configured", 400

    import urllib.parse
    redirect_uri = request.url_root + 'callback/wechat'
    params = {
        'appid': WECHAT_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'snsapi_login',
        'state': 'wechat_auth'
    }
    url = f"{WECHAT_AUTHORIZE_URL}?" + urllib.parse.urlencode(params) + "#wechat_redirect"
    return redirect(url)

@app.route('/callback/wechat')
def wechat_callback():
    """Handle the WeChat OAuth callback."""
    try:
        if not (WECHAT_CLIENT_ID and WECHAT_CLIENT_SECRET):
            return "WeChat OAuth is not configured", 400

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
            logger.error(f"WeChat token exchange failed: {token_data}")
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
            logger.error(f"WeChat user info retrieval failed: {user_info}")
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
            conn = sqlite3.connect('visitors.db')
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
        return redirect('/')
    except Exception as e:
        logger.error(f"Error during WeChat OAuth callback: {e}")
        return "WeChat authentication failed.", 400

@app.route('/logout')
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    return redirect('/')

@app.route('/profile')
@login_required
def profile():
    """Show user profile."""
    html = f'''
    <h1>用户资料</h1>
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="{current_user.profile_pic or 'https://via.placeholder.com/100'}"
                 style="width: 100px; height: 100px; border-radius: 50%; margin-right: 20px;"
                 onerror="this.src='https://via.placeholder.com/100'; this.onerror=null;">
            <div>
                <h2>{current_user.name or '未知用户'}</h2>
                <p><strong>登录提供商:</strong> {current_user.provider or 'local'}</p>
            </div>
        </div>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
            <p><strong>邮箱:</strong> {current_user.email or '未提供'}</p>
            <p><strong>用户ID:</strong> {current_user.id}</p>
            <p><strong>提供商用户ID:</strong> {current_user.provider_user_id or 'N/A'}</p>
        </div>
        <br>
        <a href="/" style="display: inline-block; padding: 10px 20px; background-color: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">返回主页</a>
        <a href="/logout" style="display: inline-block; padding: 10px 20px; background-color: #ea4335; color: white; text-decoration: none; border-radius: 4px;">退出登录</a>
    </div>
    '''
    return html

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
                <th>用户名</th>
                <th>时间戳</th>
                <th>用户代理</th>
            </tr>
        </thead>
        <tbody>
    '''

    for visitor in visitors:
        ip, timestamp, user_agent = visitor
        user_agent_display = user_agent if user_agent else "N/A"

        # Try to find user associated with this IP
        username = "访客"
        # In a real scenario, we would need to store user_id with each visit
        # For now, we'll just show current user if they're viewing their own history
        if current_user.is_authenticated:
            username = current_user.name

        html += f'''
            <tr>
                <td>{ip}</td>
                <td>{username}</td>
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

