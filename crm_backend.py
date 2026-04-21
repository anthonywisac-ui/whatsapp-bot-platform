from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
from db import decode_token, get_user, _contacts, _deals, _calls, _agents, _agent_calls, _contacts_id, _deals_id, _calls_id, _agents_id, _agent_calls_id

router = APIRouter(prefix="/api/crm", tags=["CRM"])
security = HTTPBearer()

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

# ---------- Contacts ----------
@router.get("/contacts")
def get_contacts(current_user=Depends(get_current_user)):
    return [c for c in _contacts if c.get("owner_id") == current_user["user_id"]]

@router.post("/contacts")
def create_contact(contact: dict, current_user=Depends(get_current_user)):
    global _contacts_id
    contact["id"] = _contacts_id
    contact["owner_id"] = current_user["user_id"]
    contact["created_at"] = datetime.now().isoformat()
    _contacts.append(contact)
    _contacts_id += 1
    return contact

@router.put("/contacts/{contact_id}")
def update_contact(contact_id: int, contact: dict, current_user=Depends(get_current_user)):
    for i, c in enumerate(_contacts):
        if c["id"] == contact_id and c.get("owner_id") == current_user["user_id"]:
            _contacts[i].update(contact)
            return _contacts[i]
    raise HTTPException(404, "Contact not found")

# ---------- Deals ----------
@router.get("/deals")
def get_deals(current_user=Depends(get_current_user)):
    return [d for d in _deals if d.get("owner_id") == current_user["user_id"]]

@router.post("/deals")
def create_deal(deal: dict, current_user=Depends(get_current_user)):
    global _deals_id
    deal["id"] = _deals_id
    deal["owner_id"] = current_user["user_id"]
    deal["created_at"] = datetime.now().isoformat()
    _deals.append(deal)
    _deals_id += 1
    return deal

@router.put("/deals/{deal_id}")
def update_deal(deal_id: int, deal: dict, current_user=Depends(get_current_user)):
    for i, d in enumerate(_deals):
        if d["id"] == deal_id and d.get("owner_id") == current_user["user_id"]:
            _deals[i].update(deal)
            return _deals[i]
    raise HTTPException(404, "Deal not found")

# ---------- Calls ----------
@router.get("/calls")
def get_calls(current_user=Depends(get_current_user)):
    return [c for c in _calls if c.get("owner_id") == current_user["user_id"]]

@router.post("/calls")
def create_call(call: dict, current_user=Depends(get_current_user)):
    global _calls_id
    call["id"] = _calls_id
    call["owner_id"] = current_user["user_id"]
    call["call_date"] = datetime.now().isoformat()
    _calls.append(call)
    _calls_id += 1
    return call

@router.get("/calls/kpis")
def get_kpis(current_user=Depends(get_current_user)):
    user_calls = [c for c in _calls if c.get("owner_id") == current_user["user_id"]]
    total = len(user_calls)
    resolved = len([c for c in user_calls if c.get("outcome") == "Resolved"])
    missed = len([c for c in user_calls if c.get("direction") == "Missed"])
    fcr = round(resolved / total * 100) if total else 0
    durations = [c.get("duration_minutes", 0) for c in user_calls if c.get("duration_minutes", 0) > 0]
    avg_dur = sum(durations) / len(durations) if durations else 0
    mins = int(avg_dur)
    secs = int((avg_dur - mins) * 60)
    aht = f"{mins}:{secs:02d}"
    return {"total": total, "fcr": fcr, "missed": missed, "aht": aht, "avg_duration": round(avg_dur, 1)}

# ---------- Agents ----------
@router.get("/agents/stats")
def get_agent_stats(current_user=Depends(get_current_user)):
    user_agents = [a for a in _agents if a.get("owner_id") == current_user["user_id"]]
    user_calls = [ac for ac in _agent_calls if ac.get("owner_id") == current_user["user_id"]]
    hot = len([ac for ac in user_calls if ac.get("lead_score") == "Hot Lead"])
    return {"agents": len(user_agents), "total_calls": len(user_calls), "hot_leads": hot}

@router.get("/agents/calls")
def get_agent_calls(limit: int = 50, current_user=Depends(get_current_user)):
    user_calls = [ac for ac in _agent_calls if ac.get("owner_id") == current_user["user_id"]]
    return sorted(user_calls, key=lambda x: x.get("call_date", ""), reverse=True)[:limit]

# ---------- Stats ----------
@router.get("/stats")
def get_stats(current_user=Depends(get_current_user)):
    user_contacts = [c for c in _contacts if c.get("owner_id") == current_user["user_id"]]
    user_deals = [d for d in _deals if d.get("owner_id") == current_user["user_id"]]
    active_deals = [d for d in user_deals if d.get("stage") != "Lost"]
    pipeline_value = sum(d.get("value", 0) for d in active_deals)
    hot_leads = len([c for c in user_contacts if c.get("status") == "Hot Lead"])
    return {"contacts": len(user_contacts), "deals": len(active_deals), "pipeline_value": pipeline_value, "hot_leads": hot_leads}

# ---------- AI Chat ----------
class ChatRequest(BaseModel):
    messages: list

@router.post("/ai/chat")
async def ai_chat(req: ChatRequest, current_user=Depends(get_current_user)):
    last_msg = req.messages[-1]["content"] if req.messages else ""
    reply = f"Demo reply: '{last_msg}'. Add Gemini/Groq key for real AI."
    return {"reply": reply}

# ---------- Webhook ----------
@router.get("/webhook/port")
def get_webhook_port():
    return 8000

@router.get("/webhook/events")
def get_webhook_events():
    return {"count": 0, "last_event": None}