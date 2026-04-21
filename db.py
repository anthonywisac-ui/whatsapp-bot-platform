# db.py - In-memory storage (from your original)
import time
import aiohttp
from config import MANAGER_NUMBER

customer_sessions = {}
last_message_time = {}
saved_orders = {}
customer_order_lookup = {}
manager_pending = {}
customer_profiles = {}

def save_profile(sender, session):
    if session.get("name"):
        profile = customer_profiles.get(sender, {"order_history": []})
        profile.update({
            "name": session.get("name", ""),
            "address": session.get("address", ""),
            "lang": session.get("lang", "en"),
            "delivery_type": session.get("delivery_type", ""),
            "payment": session.get("payment", ""),
        })
        if "order_history" not in profile:
            profile["order_history"] = []
        customer_profiles[sender] = profile

def add_to_order_history(sender, order_id, order_items):
    profile = customer_profiles.get(sender, {"order_history": []})
    if "order_history" not in profile:
        profile["order_history"] = []
    profile["order_history"].append({
        "order_id": order_id,
        "items": [
            {"item_id": k, "name": v["item"]["name"], "qty": v["qty"]}
            for k, v in order_items.items()
        ],
        "timestamp": time.time()
    })
    profile["order_history"] = profile["order_history"][-5:]
    customer_profiles[sender] = profile

def get_favorite_items(sender):
    profile = customer_profiles.get(sender, {})
    history = profile.get("order_history", [])
    if not history:
        return []
    item_counts = {}
    for order in history:
        for item in order.get("items", []):
            name = item.get("name") if isinstance(item, dict) else item
            if name:
                item_counts[name] = item_counts.get(name, 0) + 1
    sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
    return [item for item, count in sorted_items[:3]]

async def save_to_sheet(customer_number, session, order_id):
    # Placeholder - implement Google Sheets if needed
    print(f"Order #{order_id} saved locally")

# ========== USER AUTHENTICATION ==========
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# In-memory user store (you can later move to SQLite, but for now keep simple)
# Structure: { "username": {"hashed_password": "...", "user_id": 1, "bots": ["restaurant", ...]} }
_users_db = {}
_next_user_id = 1

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_user(username: str, password: str):
    global _next_user_id
    if username in _users_db:
        return None
    _users_db[username] = {
        "user_id": _next_user_id,
        "hashed_password": hash_password(password),
        "bots": []  # list of bot names owned by this user
    }
    _next_user_id += 1

# Modify create_user
def create_user(username: str, password: str, role: str = "user"):
    # role can be "admin" or "user"
    _users_db[username] = {
        "user_id": _next_user_id,
        "hashed_password": hash_password(password),
        "bots": [],
        "role": role
    }

    return _users_db[username]

def get_user(username: str):
    return _users_db.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Temporary in-memory storage for CRM
_contacts = []
_contacts_id = 1
_deals = []
_deals_id = 1
_calls = []
_calls_id = 1
_agents = []
_agents_id = 1
_agent_calls = []
_agent_calls_id = 1