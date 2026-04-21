from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from db import (
    get_db, get_user_by_username, decode_token, User,
    Contact, Deal, Call, VapiAgent, WhatsappBot,
    get_contacts, create_contact, get_deals, create_deal,
    get_calls, create_call, get_vapi_agents, create_vapi_agent,
    get_whatsapp_bots, create_whatsapp_bot
)
from main import get_current_user

router = APIRouter(prefix="/api/crm", tags=["CRM"])

# ========== Contacts ==========
@router.get("/contacts")
def get_contacts_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_contacts(db, current_user.id)

@router.post("/contacts")
def create_contact_api(contact: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_contact(db, current_user.id, contact)

@router.put("/contacts/{contact_id}")
def update_contact_api(contact_id: int, contact: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id, Contact.owner_id == current_user.id).first()
    if not db_contact:
        raise HTTPException(404, "Contact not found")
    for key, value in contact.items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact

# ========== Deals ==========
@router.get("/deals")
def get_deals_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_deals(db, current_user.id)

@router.post("/deals")
def create_deal_api(deal: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_deal(db, current_user.id, deal)

@router.put("/deals/{deal_id}")
def update_deal_api(deal_id: int, deal: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_deal = db.query(Deal).filter(Deal.id == deal_id, Deal.owner_id == current_user.id).first()
    if not db_deal:
        raise HTTPException(404, "Deal not found")
    for key, value in deal.items():
        setattr(db_deal, key, value)
    db.commit()
    db.refresh(db_deal)
    return db_deal

# ========== Calls ==========
@router.get("/calls")
def get_calls_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_calls(db, current_user.id)

@router.post("/calls")
def create_call_api(call: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_call(db, current_user.id, call)

@router.get("/calls/kpis")
def get_kpis_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_calls = get_calls(db, current_user.id)
    total = len(user_calls)
    resolved = len([c for c in user_calls if c.outcome == "Resolved"])
    missed = len([c for c in user_calls if c.direction == "Missed"])
    fcr = round(resolved / total * 100) if total else 0
    durations = [c.duration_minutes for c in user_calls if c.duration_minutes and c.duration_minutes > 0]
    avg_dur = sum(durations) / len(durations) if durations else 0
    mins = int(avg_dur)
    secs = int((avg_dur - mins) * 60)
    aht = f"{mins}:{secs:02d}"
    return {"total": total, "fcr": fcr, "missed": missed, "aht": aht, "avg_duration": round(avg_dur, 1)}

# ========== Agents (Vapi) ==========
@router.get("/agents")
def get_agents_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vapi_agents(db, current_user.id)

@router.post("/agents")
def create_agent_api(agent: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_vapi_agent(db, current_user.id, agent)

@router.get("/agents/stats")
def get_agent_stats_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = get_vapi_agents(db, current_user.id)
    # For stats, we would need agent_calls table – simplified for now
    return {"agents": len(agents), "total_calls": 0, "hot_leads": 0}

# ========== Whatsapp Bots ==========
@router.get("/bots")
def get_bots_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_whatsapp_bots(db, current_user.id)

@router.post("/bots")
def create_bot_api(bot: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_whatsapp_bot(db, current_user.id, bot)

# ========== Dashboard Stats ==========
@router.get("/stats")
def get_stats_api(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contacts = get_contacts(db, current_user.id)
    deals = get_deals(db, current_user.id)
    active_deals = [d for d in deals if d.stage != "Lost"]
    pipeline_value = sum(d.value for d in active_deals)
    hot_leads = len([c for c in contacts if c.status == "Hot Lead"])
    return {
        "contacts": len(contacts),
        "deals": len(active_deals),
        "pipeline_value": pipeline_value,
        "hot_leads": hot_leads
    }

# ========== AI Chat (placeholder) ==========
class ChatRequest(BaseModel):
    messages: list

@router.post("/ai/chat")
async def ai_chat(req: ChatRequest, current_user: User = Depends(get_current_user)):
    last_msg = req.messages[-1]["content"] if req.messages else ""
    reply = f"Demo reply: '{last_msg}'. Add Gemini/Groq key for real AI."
    return {"reply": reply}

# ========== Webhook Info ==========
@router.get("/webhook/port")
def get_webhook_port():
    return 8000

@router.get("/webhook/events")
def get_webhook_events():
    return {"count": 0, "last_event": None}