# main.py - Global entry point that loads bot based on BOT_TYPE
import os
import importlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
import uvicorn
import stripe
from config import STRIPE_SECRET_KEY, ADMIN_SECRET
from session import SharedSession
from cms.routes import router as cms_router
app.include_router(cms_router)
from fastapi.staticfiles import StaticFiles

# After creating app, mount static folder
app.mount("/cms/static", StaticFiles(directory="cms/static", html=True), name="cms_static")

# Optional: redirect root to admin panel
@app.get("/")
async def admin_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/cms/static/index.html")
stripe.api_key = STRIPE_SECRET_KEY

BOT_TYPE = os.getenv("BOT_TYPE", "restaurant")

# Dynamically import the bot's module
bot_module = importlib.import_module(f"bots.{BOT_TYPE}.main")
app = bot_module.app

@app.on_event("shutdown")
async def shutdown():
    await SharedSession.close_session()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
