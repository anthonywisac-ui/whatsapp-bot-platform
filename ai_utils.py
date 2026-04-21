import aiohttp
from config import GROQ_API_KEY
from session import SharedSession

async def get_ai_response(sender, user_message, lang="en", session=None, extra_instruction=""):
    system_prompt = """You are a friendly customer service assistant. Be concise, warm, and helpful. Reply in the same language as the user."""
    messages = [{"role": "system", "content": system_prompt}]
    if session and session.get("conversation"):
        messages.extend(session["conversation"][-6:])
    messages.append({"role": "user", "content": user_message})
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 150
    }
    try:
        shared_session = await SharedSession.get_session()
        async with shared_session.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers) as r:
            result = await r.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"AI Error: {e}")
        return "Sorry, I'm having trouble. Please try again."
