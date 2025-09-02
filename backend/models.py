from pydantic import BaseModel, Field

class SeedItem(BaseModel):
    topic: str
    section: str
    classification: str = Field(pattern="^(public|internal|restricted)$")
    text: str

class SeedPayload(BaseModel):
    admin_secret: str
    policies: list[SeedItem] = []
    customers: list[dict] = []

class VerificationRequest(BaseModel):
    email: str
    full_name: str = ""
    last4: str = ""
    order_id: str = ""

class PolicyQuery(BaseModel):
    topic: str
    detail_level: str = "summary"  # summary|full