# database.py
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional, List, Dict, Any

# ========== Database Setup ==========
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./platform.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== Password & JWT ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    from jose import jwt
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ========== Models ==========
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    bots_json = Column(Text, default="[]")  # store bot names as JSON list
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contacts = relationship("Contact", back_populates="owner", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="owner", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="owner", cascade="all, delete-orphan")
    vapi_agents = relationship("VapiAgent", back_populates="owner", cascade="all, delete-orphan")
    whatsapp_bots = relationship("WhatsappBot", back_populates="owner", cascade="all, delete-orphan")

    @property
    def bots(self) -> List[str]:
        return json.loads(self.bots_json or "[]")

    @bots.setter
    def bots(self, value: List[str]):
        self.bots_json = json.dumps(value)

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    company = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    status = Column(String, default="New")
    source = Column(String, default="Manual")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="contacts")

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Deal")
    company = Column(String, default="")
    contact_name = Column(String, default="")
    value = Column(Float, default=0.0)
    stage = Column(String, default="Discovery")
    probability = Column(Integer, default=20)
    expected_close = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="deals")

class Call(Base):
    __tablename__ = "calls"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_name = Column(String, default="Unknown")
    phone = Column(String, default="")
    direction = Column(String, default="Inbound")
    duration_minutes = Column(Float, default=0.0)
    outcome = Column(String, default="Resolved")
    agent = Column(String, default="")
    notes = Column(Text, default="")
    call_date = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="calls")

class VapiAgent(Base):
    __tablename__ = "vapi_agents"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    vapi_api_key = Column(String, default="")
    vapi_agent_id = Column(String, default="")
    phone_number = Column(String, default="")
    system_prompt = Column(Text, default="")
    voice = Column(String, default="")
    first_message = Column(Text, default="")
    webhook_url = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="vapi_agents")

class WhatsappBot(Base):
    __tablename__ = "whatsapp_bots"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    bot_type = Column(String, default="order")
    meta_token = Column(String, default="")
    phone_number_id = Column(String, default="")
    waba_id = Column(String, default="")
    verify_token = Column(String, default="")
    ai_provider = Column(String, default="groq")
    ai_api_key = Column(String, default="")
    manager_number = Column(String, default="")
    google_sheet_id = Column(String, default="")
    google_creds_json = Column(Text, default="")
    language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="whatsapp_bots")

# Create tables
Base.metadata.create_all(bind=engine)

# ========== Database Session Dependency ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== Helper Functions (to mimic old db.py API) ==========
# These functions maintain compatibility with existing routes

def create_user(db, username: str, password: str, role: str = "user") -> Optional[User]:
    if db.query(User).filter(User.username == username).first():
        return None
    hashed = hash_password(password)
    user = User(username=username, hashed_password=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# Add more CRUD helpers as needed for contacts, deals, calls, etc.
# (to keep existing route code unchanged, you can add functions like get_contacts, create_contact, etc.)

def get_contacts(db, owner_id: int):
    return db.query(Contact).filter(Contact.owner_id == owner_id).all()

def create_contact(db, owner_id: int, data: dict):
    contact = Contact(owner_id=owner_id, **data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_deals(db, owner_id: int):
    return db.query(Deal).filter(Deal.owner_id == owner_id).all()

def create_deal(db, owner_id: int, data: dict):
    deal = Deal(owner_id=owner_id, **data)
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal

def get_calls(db, owner_id: int):
    return db.query(Call).filter(Call.owner_id == owner_id).all()

def create_call(db, owner_id: int, data: dict):
    call = Call(owner_id=owner_id, **data)
    db.add(call)
    db.commit()
    db.refresh(call)
    return call

def get_vapi_agents(db, owner_id: int):
    return db.query(VapiAgent).filter(VapiAgent.owner_id == owner_id).all()

def create_vapi_agent(db, owner_id: int, data: dict):
    agent = VapiAgent(owner_id=owner_id, **data)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

def get_whatsapp_bots(db, owner_id: int):
    return db.query(WhatsappBot).filter(WhatsappBot.owner_id == owner_id).all()

def create_whatsapp_bot(db, owner_id: int, data: dict):
    bot = WhatsappBot(owner_id=owner_id, **data)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot