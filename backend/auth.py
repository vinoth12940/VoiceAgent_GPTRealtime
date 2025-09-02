import httpx
from fastapi import HTTPException
from .config import OPENAI_API_KEY, REALTIME_MODEL, REALTIME_VOICE, REALTIME_SESSIONS_URL

# Simple in-memory session flags (swap for Redis in prod)
SESSION_FLAGS: dict[str, dict] = {}

def set_verified(session_id: str, value: bool):
    SESSION_FLAGS.setdefault(session_id, {})["verified"] = value

def is_verified(session_id: str) -> bool:
    return bool(SESSION_FLAGS.get(session_id, {}).get("verified"))

async def create_ephemeral_session():
    """
    Create an ephemeral Realtime session token using the server-side API key.
    The returned JSON includes client_secret (short-lived) used by the browser.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY not configured")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1"
    }
    
    body = {
        "model": REALTIME_MODEL,    # "gpt-realtime"
        "voice": REALTIME_VOICE,    # e.g., "marin"
        "modalities": ["audio", "text"],
        "input_audio_format": "pcm16",
        "tools": [
            {
                "type": "function",
                "name": "verify_customer",
                "description": "Verify a customer before sharing non-public information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "Customer email address"},
                        "full_name": {"type": "string", "description": "Customer full name"},
                        "last4": {"type": "string", "description": "Last 4 digits of payment method"},
                        "order_id": {"type": "string", "description": "Order ID for verification"}
                    },
                    "required": ["email"]
                }
            },
            {
                "type": "function",
                "name": "get_policy",
                "description": "Fetch a policy by topic. Only use after verification for internal/restricted policies",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Policy topic to search for"},
                        "detail_level": {
                            "type": "string", 
                            "enum": ["summary", "full"],
                            "description": "Level of detail to return"
                        }
                    },
                    "required": ["topic"]
                }
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(REALTIME_SESSIONS_URL, headers=headers, json=body)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
        result = r.json()
        
        # Extract the client_secret value from the nested structure
        client_secret = result.get('client_secret', {}).get('value')
        if not client_secret:
            raise HTTPException(500, "No client_secret in response")
        
        # Return the session with the extracted client_secret
        return {
            "id": result.get('id'),
            "client_secret": client_secret,
            "model": result.get('model'),
            "voice": result.get('voice')
        }