import os
import importlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
import uvicorn
import stripe
from pydantic import BaseModel
from config import STRIPE_SECRET_KEY
from session import SharedSession
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db import authenticate_user, create_access_token, get_user, decode_token, _users_db
from crm_backend import router as crm_router

security = HTTPBearer()

stripe.api_key = STRIPE_SECRET_KEY

BOT_TYPE = os.getenv("BOT_TYPE", "restaurant")

# Dynamically import the bot's module
bot_module = importlib.import_module(f"bots.{BOT_TYPE}.main")
app = bot_module.app
app.include_router(crm_router)
# ========== ADD THIS BLOCK ==========
static_dir = os.path.join(os.path.dirname(__file__), "cms", "static")
if os.path.exists(static_dir):
    app.mount("/cms/static", StaticFiles(directory=static_dir, html=True), name="cms_static")
    print("✅ CMS static files mounted")
else:
    print(f"⚠️ CMS static directory not found at {static_dir}")
# ====================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=401)
    return user

class RegisterRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
def register(req: RegisterRequest):
    user = create_user(req.username, req.password, role="user")
    if not user:
        raise HTTPException(status_code=400, detail="Username exists")
    return {"msg": "User created"}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user, "user_id": current_user["user_id"], "bots": current_user["bots"]}

@app.get("/create-admin")
def create_admin():
    from db import create_user
    user = create_user("admin", "your_strong_password", role="admin")
    if user:
        return {"msg": "Admin user created"}
    else:
        return {"msg": "Admin already exists"}

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