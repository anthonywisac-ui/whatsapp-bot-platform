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
