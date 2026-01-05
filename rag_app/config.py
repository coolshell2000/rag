import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL_NAME = "shibing624/text2vec-base-chinese"
CROSS_ENCODER_MODEL_NAME = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
CHROMADB_COLLECTION_NAME = "default"
GEMINI_MODEL = "gemini-2.0-flash"

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# WeChat OAuth Configuration
WECHAT_CLIENT_ID = os.getenv("WECHAT_CLIENT_ID")
WECHAT_CLIENT_SECRET = os.getenv("WECHAT_CLIENT_SECRET")
WECHAT_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"