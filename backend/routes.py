from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from . import db, auth
from .models import SeedPayload, VerificationRequest, PolicyQuery
from .config import ADMIN_SECRET

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/policies")
def api_list_policies():
    return db.list_policies()

@router.post("/seed")
def api_seed(payload: SeedPayload):
    if payload.admin_secret != ADMIN_SECRET:
        raise HTTPException(401, "Unauthorized")
    policies = [p.dict() for p in payload.policies]
    customers = payload.customers
    db.seed_many(policies, customers)
    return {"ok": True, "policies": len(policies), "customers": len(customers)}

@router.post("/verify")
def api_verify(req: VerificationRequest, x_session_id: str = Header(default="anon")):
    ok = db.verify_customer(req.email, req.full_name, req.last4, req.order_id)
    if ok:
        auth.set_verified(x_session_id, True)
        db.log("customer", "verification_success", req.email)
        return {"verified": True}
    db.log("customer", "verification_failed", req.email)
    return JSONResponse({"verified": False}, status_code=403)

@router.post("/policy")
def api_policy(q: PolicyQuery, x_session_id: str = Header(default="anon")):
    policy = db.get_policy(q.topic)
    if not policy:
        db.log("agent", "policy_not_found", q.topic)
        raise HTTPException(404, "Policy not found")

    classification = policy["classification"]
    if classification in ("internal", "restricted") and not auth.is_verified(x_session_id):
        db.log("agent", "policy_access_denied", f"{q.topic}:{classification}")
        raise HTTPException(403, "Verification required")

    db.log("agent", "policy_access_granted", f"{q.topic}:{classification}:{q.detail_level}")
    text = policy["text"]
    if q.detail_level == "summary":
        text = text.strip().split("\n\n")[0]
    return {
        "topic": policy["topic"],
        "section": policy["section"],
        "classification": classification,
        "text": text,
        "updated_at": policy["updated_at"]
    }

@router.get("/audits")
def api_audits():
    return db.list_audits()

@router.post("/realtime/session")
async def api_realtime_session():
    """Create ephemeral session for WebSocket connection"""
    return await auth.create_ephemeral_session()

@router.get("/realtime/token")
async def api_realtime_token():
    """Create ephemeral token for WebRTC connection"""
    import httpx
    from .config import OPENAI_API_KEY
    
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY not configured")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create ephemeral token for WebRTC - using the sessions endpoint
    body = {
        "model": "gpt-4o-realtime-preview-2024-10-01",
        "voice": "shimmer",
        "modalities": ["audio", "text"]
    }
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            r = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers=headers,
                json=body
            )
            r.raise_for_status()
            result = r.json()
            
            print(f"✅ Ephemeral token created: {result}")
            
            # Extract client_secret from the response
            client_secret = result.get('client_secret', {})
            if isinstance(client_secret, dict):
                client_secret_value = client_secret.get('value')
            else:
                client_secret_value = client_secret
            
            if not client_secret_value:
                raise HTTPException(500, f"No client_secret in response: {result}")
            
            return {
                "client_secret": client_secret_value,
                "expires_at": result.get("expires_at"),
                "session_id": result.get("id")
            }
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            print(f"❌ Token creation failed: {error_text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"OpenAI API error: {error_text}")

@router.get("/policy/search")
def api_policy_search(q: str, x_session_id: str = Header(default="anon")):
    """Search policies by topic with fuzzy matching"""
    if not q or len(q.strip()) < 2:
        raise HTTPException(400, "Search query must be at least 2 characters")
    
    # Check verification for internal/restricted policies
    policies = db.search_policies(q.strip())
    
    # Filter out internal/restricted policies if not verified
    if not auth.is_verified(x_session_id):
        policies = [p for p in policies if p["classification"] not in ("internal", "restricted")]
    
    return policies

# ===== Customer Policy Details API =====
@router.get("/customer/{email}/policies")
def api_get_customer_policies(email: str, x_session_id: str = Header(default="anon")):
    """Get all policies for a customer (requires verification)"""
    if not auth.is_verified(x_session_id):
        raise HTTPException(403, "Customer verification required")
    
    policies = db.get_customer_policies(email)
    db.log("agent", "customer_policies_accessed", email)
    return policies

@router.get("/policy-details/{policy_number}")
def api_get_policy_details(policy_number: str, x_session_id: str = Header(default="anon")):
    """Get detailed policy information by policy number (requires verification)"""
    if not auth.is_verified(x_session_id):
        raise HTTPException(403, "Customer verification required")
    
    policy = db.get_policy_by_number(policy_number)
    if not policy:
        raise HTTPException(404, "Policy not found")
    
    db.log("agent", "policy_details_accessed", policy_number)
    return policy

@router.post("/policy-status/{policy_number}")
def api_update_policy_status(policy_number: str, status: str, x_session_id: str = Header(default="anon")):
    """Update policy status (requires verification)"""
    if not auth.is_verified(x_session_id):
        raise HTTPException(403, "Customer verification required")
    
    if status not in ["active", "inactive"]:
        raise HTTPException(400, "Status must be 'active' or 'inactive'")
    
    policy = db.get_policy_by_number(policy_number)
    if not policy:
        raise HTTPException(404, "Policy not found")
    
    db.update_policy_status(policy_number, status)
    db.log("agent", "policy_status_updated", f"{policy_number}:{status}")
    return {"policy_number": policy_number, "status": status}

# ===== P&C Insurance Specific APIs =====
@router.get("/pc-policies/auto")
def api_get_auto_policies(x_session_id: str = Header(default="anon")):
    """Get all auto insurance policies for verified customer"""
    if not auth.is_verified(x_session_id):
        raise HTTPException(403, "Customer verification required")
    
    policies = db.search_policies("auto")
    return [p for p in policies if "auto" in p["topic"].lower()]

@router.get("/pc-policies/property")
def api_get_property_policies(x_session_id: str = Header(default="anon")):
    """Get all property insurance policies for verified customer"""
    if not auth.is_verified(x_session_id):
        raise HTTPException(403, "Customer verification required")
    
    policies = db.search_policies("home")
    return [p for p in policies if "home" in p["topic"].lower() or "property" in p["topic"].lower()]

@router.get("/pc-coverage/{coverage_type}")
def api_get_coverage_info(coverage_type: str, x_session_id: str = Header(default="anon")):
    """Get P&C coverage information by type"""
    valid_types = ["auto", "homeowners", "commercial", "liability", "claims"]
    if coverage_type not in valid_types:
        raise HTTPException(400, f"Coverage type must be one of: {valid_types}")
    
    # Map coverage types to actual policy topics
    topic_mapping = {
        "auto": "auto_coverage_limits",
        "homeowners": "homeowners_coverage",
        "commercial": "commercial_liability",
        "liability": "commercial_liability",
        "claims": "claims_process"
    }
    
    topic = topic_mapping.get(coverage_type, coverage_type)
    policy = db.get_policy(topic)
    
    if not policy:
        raise HTTPException(404, "Coverage information not found")
    
    # Filter based on verification for internal/restricted content
    if policy["classification"] in ("internal", "restricted") and not auth.is_verified(x_session_id):
        raise HTTPException(403, "Verification required for detailed coverage information")
    
    return policy