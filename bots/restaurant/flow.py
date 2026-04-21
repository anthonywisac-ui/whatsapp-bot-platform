# flow.py - Simplified version of your original restaurant flow
import time, random, re, traceback
from .db import customer_sessions, saved_orders, customer_profiles, manager_pending
from .config import MIN_DELIVERY_ORDER, MIN_PICKUP_ORDER, POST_ORDER_WINDOW, LANG_NAMES
from .strings import t
from .utils import get_order_total, get_delivery_fee, get_order_text, find_item, is_valid_name, is_valid_address, is_order_status_query, is_thanks, is_bye, is_menu_request, guess_category, extract_order_number, truncate_title, safe_btn
from .whatsapp_handlers import send_text_message, send_main_menu, send_category_items, send_qty_control, send_cart_view, send_order_summary, send_delivery_buttons, send_payment_buttons, send_order_confirmed
from .ai_utils import get_ai_response
from .menu_data import MENU
from .stripe_utils import create_stripe_checkout_session

def new_session(sender=None, table_number=None):
    return {"stage": "lang_select", "lang": "en", "order": {}, "delivery_type": "", "address": "", "name": "", "payment": "", "last_added": None, "conversation": [], "post_order_at": 0}

def get_session(sender):
    if sender not in customer_sessions:
        customer_sessions[sender] = new_session(sender)
    return customer_sessions[sender]

async def handle_flow(sender, text, is_button=False):
    session = get_session(sender)
    lang = session.get("lang", "en")
    # Simplified flow - you can replace with your full flow.py
    if session["stage"] == "lang_select":
        if text.startswith("LANG_"):
            session["lang"] = text.replace("LANG_", "").lower()
            session["stage"] = "menu"
            await send_text_message(sender, t(lang, "greeting_welcome"))
            await send_main_menu(sender, session["order"], lang)
        else:
            from .whatsapp_handlers import send_language_selection
            await send_language_selection(sender)
    elif session["stage"] == "menu":
        if text == "CHECKOUT":
            await send_order_summary(sender, session["order"], lang)
            session["stage"] = "confirm"
        else:
            await send_main_menu(sender, session["order"], lang)
    else:
        await send_text_message(sender, "Type *menu* to see options")
