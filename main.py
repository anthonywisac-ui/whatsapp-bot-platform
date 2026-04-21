import os
import importlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
import uvicorn
import stripe
from config import STRIPE_SECRET_KEY
from session import SharedSession

stripe.api_key = STRIPE_SECRET_KEY

BOT_TYPE = os.getenv("BOT_TYPE", "restaurant")

# Dynamically import the bot's module
bot_module = importlib.import_module(f"bots.{BOT_TYPE}.main")
app = bot_module.app

# ========== ADD THIS BLOCK ==========
static_dir = os.path.join(os.path.dirname(__file__), "cms", "static")
if os.path.exists(static_dir):
    app.mount("/cms/static", StaticFiles(directory=static_dir, html=True), name="cms_static")
    print("✅ CMS static files mounted")
else:
    print(f"⚠️ CMS static directory not found at {static_dir}")
# ====================================

# ========== CMS ROUTES (if exists) ==========
try:
    from cms.routes import router as cms_router
    app.include_router(cms_router)
    print("✅ CMS routes mounted")
except ImportError:
    print("⚠️ CMS module not found, skipping")

@app.on_event("shutdown")
async def shutdown():
    await SharedSession.close_session()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)