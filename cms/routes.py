from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import SessionLocal, BotConfig, AdminUser
from .auth import verify_password, get_password_hash, create_access_token, decode_token
from pydantic import BaseModel
import subprocess
import json
import os

router = APIRouter(prefix="/cms", tags=["CMS"])
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/setup")
def setup_admin():
    # First-time setup – create admin user if none exists
    db = SessionLocal()
    admin = db.query(AdminUser).first()
    if not admin:
        default_password = os.getenv("ADMIN_PASSWORD", "admin123")
        hashed = get_password_hash(default_password)
        admin = AdminUser(username="admin", hashed_password=hashed)
        db.add(admin)
        db.commit()
        return {"message": f"Admin created. Username: admin, Password: {default_password}"}
    return {"message": "Admin already exists"}

# ---------- Bot CRUD ----------
class BotConfigCreate(BaseModel):
    name: str
    bot_type: str
    config_json: dict

@router.post("/bots", dependencies=[Depends(get_current_admin)])
def create_bot(bot: BotConfigCreate, db: Session = Depends(get_db)):
    # Check if bot already exists in filesystem
    bot_path = f"bots/{bot.name}"
    if os.path.exists(bot_path):
        raise HTTPException(status_code=400, detail="Bot folder already exists")
    # Save config to database
    db_bot = BotConfig(name=bot.name, bot_type=bot.bot_type, config_json=json.dumps(bot.config_json))
    db.add(db_bot)
    db.commit()
    # Call generator script
    config_file = f"/tmp/{bot.name}_config.json"
    with open(config_file, "w") as f:
        json.dump(bot.config_json, f, indent=2)
    result = subprocess.run(["python", "generate_bot.py", config_file], capture_output=True, text=True)
    os.remove(config_file)
    if result.returncode != 0:
        # Rollback
        db.delete(db_bot)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Generator failed: {result.stderr}")
    return {"message": f"Bot {bot.name} created", "output": result.stdout}

@router.get("/bots", dependencies=[Depends(get_current_admin)])
def list_bots(db: Session = Depends(get_db)):
    bots = db.query(BotConfig).all()
    return [{"id": b.id, "name": b.name, "type": b.bot_type, "created": b.created_at} for b in bots]

@router.delete("/bots/{bot_name}", dependencies=[Depends(get_current_admin)])
def delete_bot(bot_name: str, db: Session = Depends(get_db)):
    import shutil
    bot_path = f"bots/{bot_name}"
    if not os.path.exists(bot_path):
        raise HTTPException(status_code=404, detail="Bot not found")
    shutil.rmtree(bot_path)
    db.query(BotConfig).filter(BotConfig.name == bot_name).delete()
    db.commit()
    return {"message": f"Bot {bot_name} deleted"}