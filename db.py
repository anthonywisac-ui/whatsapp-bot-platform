# db.py – SQLAlchemy models + session management
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from passlib.context import CryptContext
from jose import JWTError, jwt
import json

# ========== Database Setup ==========
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== Password & JWT ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    from jose import jwt
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ========== Models ==========
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    bots = relationship("Bot", back_populates="owner")
    contacts = relationship("Contact", back_populates="owner")
    deals = relationship("Deal", back_populates="owner")
    calls = relationship("Call", back_populates="owner")
    agents = relationship("Agent", back_populates="owner")

class Bot(Base):
    __tablename__ = "bots"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    bot_type = Column(String)
    config_json = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="bots")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    company = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    status = Column(String, default="New")
    source = Column(String, default="Manual")
    notes = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="contacts")

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True)
    title = Column(String, default="New Deal")
    company = Column(String, default="")
    contact_name = Column(String, default="")
    value = Column(Float, default=0.0)
    stage = Column(String, default="Discovery")
    probability = Column(Integer, default=20)
    expected_close = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="deals")

class Call(Base):
    __tablename__ = "calls"
    id = Column(Integer, primary_key=True)
    contact_name = Column(String, default="Unknown")
    phone = Column(String, default="")
    direction = Column(String, default="Inbound")
    duration_minutes = Column(Float, default=0.0)
    outcome = Column(String, default="Resolved")
    agent = Column(String, default="")
    notes = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id"))
    call_date = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="calls")

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, unique=True, index=True)
    agent_name = Column(String)
    description = Column(String, default="")
    fields = Column(Text, default="[]")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="agents")

class AgentCall(Base):
    __tablename__ = "agent_calls"
    id = Column(Integer, primary_key=True)
    call_id = Column(String, unique=True)
    agent_id = Column(String)
    agent_name = Column(String)
    contact_name = Column(String, default="Unknown")
    phone = Column(String, default="")
    email = Column(String, default="")
    duration_min = Column(Float, default=0.0)
    lead_score = Column(String, default="New")
    transcript = Column(Text, default="")
    structured = Column(Text, default="{}")
    summary = Column(Text, default="")
    contact_ref = Column(Integer, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    call_date = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User")

# Create tables
Base.metadata.create_all(bind=engine)

# ========== Database Helpers ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# User CRUD
def get_user_by_username(db, username):
    return db.query(User).filter(User.username == username).first()

def create_user(db, username, password, role="user"):
    if get_user_by_username(db, username):
        return None
    hashed = hash_password(password)
    user = User(username=username, hashed_password=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db, username, password):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# Bot CRUD (example – add others as needed)
def get_bot_by_name(db, name, owner_id):
    return db.query(Bot).filter(Bot.name == name, Bot.owner_id == owner_id).first()

def create_bot(db, name, bot_type, config_json, owner_id):
    bot = Bot(name=name, bot_type=bot_type, config_json=json.dumps(config_json), owner_id=owner_id)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

def get_bots_for_user(db, owner_id):
    return db.query(Bot).filter(Bot.owner_id == owner_id).all()