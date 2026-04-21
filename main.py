import os
import importlib
from fastapi import FastAPI
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

# ========== CMS ROUTES (only if CMS folder exists) ==========
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