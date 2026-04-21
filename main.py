import os
import importlib
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import (
    get_db, get_user_by_username, authenticate_user,
    create_access_token, decode_token, create_user, User
)
import uvicorn

app = FastAPI()

# ========== Security ==========
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401)
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401)
    return user

# ========== Auth Models ==========
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

# ========== Auth Endpoints ==========
@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user = create_user(db, req.username, req.password, role="user")
    if not user:
        raise HTTPException(status_code=400, detail="Username exists")
    return {"msg": "User created"}

@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "user_id": current_user.id,
        "bots": current_user.bots  # from bots_json property
    }

# ========== Initial Admin Creation (only if no users) ==========
@app.on_event("startup")
def create_initial_admin():
    from db import SessionLocal, User
    db = SessionLocal()
    if db.query(User).count() == 0:
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        create_user(db, "admin", admin_password, role="admin")
        print("✅ Initial admin created (username: admin)")
    db.close()

# ========== Bot Mounting (with validation) ==========
ALLOWED_BOT_TYPES = ["restaurant", "order", "appointment", "real_estate", "ecommerce", "hair_salon", "gym"]

def load_bot_module(bot_type: str):
    if bot_type not in ALLOWED_BOT_TYPES:
        raise ValueError(f"Invalid BOT_TYPE: {bot_type}. Allowed: {ALLOWED_BOT_TYPES}")
    return importlib.import_module(f"bots.{bot_type}.main")

BOT_TYPE = os.getenv("BOT_TYPE", "restaurant")
try:
    bot_module = load_bot_module(BOT_TYPE)
    app.mount("/", bot_module.app)  # mount bot routes (webhook etc.)
except Exception as e:
    print(f"⚠️ Bot module not loaded: {e}")

# ========== Static Files (CMS) ==========
static_dir = os.path.join(os.path.dirname(__file__), "cms", "static")
if os.path.exists(static_dir):
    app.mount("/cms/static", StaticFiles(directory=static_dir, html=True), name="cms_static")

# ========== CRM Routes (from crm_backend.py) ==========
from crm_backend import router as crm_router
app.include_router(crm_router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)