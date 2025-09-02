import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import websockets
import asyncio
import json

from . import db
from .routes import router as api_router
from .config import APP_ORIGIN, REALTIME_MODEL
from .auth import create_ephemeral_session

app = FastAPI(title="Voice Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_ORIGIN, "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# WebSocket proxy for GPT Realtime
@app.websocket("/ws/realtime")
async def websocket_realtime_proxy(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Create session with OpenAI
        session = await create_ephemeral_session()
        client_secret = session["client_secret"]
        
        # Connect to OpenAI Realtime API
        openai_ws_url = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"
        headers = [
            ("Authorization", f"Bearer {client_secret}"),
            ("OpenAI-Beta", "realtime=v1")
        ]
        
        async with websockets.connect(openai_ws_url, additional_headers=headers) as openai_ws:
            print(f"✅ Connected to OpenAI Realtime API")
            
            # Initialize session according to Realtime API
            print("🚀 Initializing Realtime session...")
            
            # Configure session following latest OpenAI prompting guide (Aug 28, 2025)
            instructions = """# Role & Objective
You are a professional P&C (Property & Casualty) insurance customer service specialist. Your task is to verify customer identities and provide accurate information about their auto, home, commercial, and umbrella insurance policies.

# Personality & Tone
## Personality
- Friendly, professional, and empathetic insurance expert
- Calm and approachable customer service assistant

## Tone
- Warm, concise, confident, never fawning
- Professional but conversational

## Length
- 1-2 sentences per turn
- Keep responses brief and direct

## Pacing
- Deliver your audio response at a natural pace
- Do not sound rushed or robotic

# Instructions
- ALWAYS verify customer identity before sharing policy details
- Ask for email, full name, and last 4 digits of phone number for verification
- Use your tools proactively: verify_customer then get_customer_policies
- Provide specific P&C policy information: coverage types, premiums, deductibles, due dates
- Explain insurance terms clearly (liability limits, comprehensive, collision, HO-3, etc.)
- Only respond to clear audio or text
- If audio is unclear/partial/noisy/silent, ask for clarification

# Tools
- Before any tool call, say one short line like "Let me check that for you" then call the tool immediately
- Use verify_customer first, then get_customer_policies for verified customers
- Use get_pc_coverage_info for general coverage questions

# Conversation Flow
## Greeting
Goal: Set tone and invite the reason for calling
- Identify as P&C insurance specialist
- Keep brief; invite caller's goal
Sample phrases (vary responses):
- "Thanks for calling. I'm your P&C insurance specialist. How can I help you today?"
- "Hello, this is your insurance support. What can I help you with?"

## Verification
Goal: Confirm customer identity before sharing policy details
- Request email, full name, and last 4 digits of phone
- Use verification tool immediately after collecting information

## Resolution  
Goal: Provide requested policy information
- Share specific coverage details, premiums, and policy terms
- Explain P&C terminology when needed

## Closing
Goal: Ensure customer satisfaction
- Ask if there's anything else you can help with
- End warmly and professionally

# Variety
- Do not repeat the same sentence twice
- Vary your responses so it doesn't sound robotic

# Safety & Escalation
When to escalate (no extra troubleshooting):
- User explicitly asks for a human
- Severe dissatisfaction or frustration
- 2 failed tool attempts on the same task
- Out-of-scope requests (legal advice, real-time news)

What to say when escalating:
- "I'm connecting you with a specialist who can better assist you"
- Then use appropriate escalation method"""

            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": instructions,
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {"type": "server_vad"},
                    "tools": [
                        {
                            "type": "function",
                            "name": "verify_customer",
                            "description": "Verify P&C insurance customer identity",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "full_name": {"type": "string"},
                                    "last4": {"type": "string"},
                                    "order_id": {"type": "string"}
                                },
                                "required": ["email"]
                            }
                        },
                        {
                            "type": "function",
                            "name": "get_customer_policies",
                            "description": "Get all P&C policies (auto, home, commercial, umbrella) for verified customer",
                            "parameters": {
                                "type": "object",
                                "properties": {"email": {"type": "string"}},
                                "required": ["email"]
                            }
                        },
                        {
                            "type": "function",
                            "name": "get_pc_coverage_info",
                            "description": "Get P&C coverage information by type (auto, homeowners, commercial, liability, claims)",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "coverage_type": {"type": "string", "enum": ["auto", "homeowners", "commercial", "liability", "claims"]}
                                },
                                "required": ["coverage_type"]
                            }
                        }
                    ]
                }
            }))
            
            print("✅ Session configured, ready to proxy messages")
            
            # Send initial greeting to start the conversation
            await openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "Please introduce yourself as a customer service assistant and ask how you can help today."
                }
            }))
            
            # Handle tool calls
            async def handle_tool_call(tool_call_data):
                from .auth import set_verified, is_verified
                
                tool_name = tool_call_data.get("function", {}).get("name")
                tool_args = json.loads(tool_call_data.get("arguments", "{}"))
                call_id = tool_call_data.get("id")
                
                print(f"🔧 Handling tool call: {tool_name} with args: {tool_args}")
                
                if tool_name == "verify_customer":
                    # Verify customer
                    result = db.verify_customer(
                        tool_args.get("email", ""),
                        tool_args.get("full_name", ""),
                        tool_args.get("last4", ""),
                        tool_args.get("order_id", "")
                    )
                    set_verified("default_session", result)
                    
                    print(f"✅ Customer verification result: {result}")
                    
                    # Send result back to OpenAI using conversation.item.create
                    await openai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps({"verified": result})
                        }
                    }))
                    
                    # Trigger response after tool call
                    await openai_ws.send(json.dumps({
                        "type": "response.create"
                    }))
                    

                
                elif tool_name == "get_customer_policies":
                    if not is_verified("default_session"):
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps({"error": "verification_required", "message": "Customer must be verified to access P&C policy details"})
                            }
                        }))
                        
                        await openai_ws.send(json.dumps({
                            "type": "response.create"
                        }))
                    else:
                        email = tool_args.get("email", "")
                        policies = db.get_customer_policies(email)
                        
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps({"policies": policies, "count": len(policies)})
                            }
                        }))
                        
                        await openai_ws.send(json.dumps({
                            "type": "response.create"
                        }))
                
                elif tool_name == "get_pc_coverage_info":
                    coverage_type = tool_args.get("coverage_type", "")
                    
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
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps({"error": "Coverage information not found"})
                            }
                        }))
                        
                        await openai_ws.send(json.dumps({
                            "type": "response.create"
                        }))
                    else:
                        # Check if verification is required for internal/restricted content
                        if policy["classification"] in ("internal", "restricted") and not is_verified("default_session"):
                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": json.dumps({"error": "verification_required", "message": "Verification required for detailed coverage information"})
                                }
                            }))
                            
                            await openai_ws.send(json.dumps({
                                "type": "response.create"
                            }))
                        else:
                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": json.dumps(policy)
                                }
                            }))
                            
                            await openai_ws.send(json.dumps({
                                "type": "response.create"
                            }))
                

            
            # Proxy messages between frontend and OpenAI
            async def forward_to_openai():
                try:
                    async for message in websocket.iter_text():
                        try:
                            data = json.loads(message)
                            print(f"📤 Frontend -> OpenAI: {data.get('type', 'unknown')}")
                            
                            # Filter out invalid test messages
                            if data.get("type") == "test":
                                print("🧪 Ignoring test message from frontend")
                                continue
                                
                            await openai_ws.send(message)
                        except json.JSONDecodeError:
                            print(f"⚠️ Invalid JSON from frontend: {message}")
                        except Exception as e:
                            print(f"⚠️ Error forwarding to OpenAI: {e}")
                            break
                except WebSocketDisconnect:
                    print("🔌 Frontend disconnected")
                except Exception as e:
                    print(f"⚠️ Forward to OpenAI error: {e}")
            
            async def forward_to_frontend():
                try:
                    async for message in openai_ws:
                        try:
                            data = json.loads(message)
                            event_type = data.get('type', 'unknown')
                            print(f"📥 OpenAI -> Frontend: {event_type}")
                            
                            # Log error details for debugging
                            if data.get('type') == 'error':
                                print(f"❌ OpenAI Error: {json.dumps(data, indent=2)}")
                            
                            # Log response.done events to see if they contain function calls
                            if event_type == 'response.done':
                                output = data.get('response', {}).get('output', [])
                                for item in output:
                                    if item.get('type') == 'function_call':
                                        print(f"🔧 Found function call in response.done: {item.get('name')}")
                                        tool_call_data = {
                                            "function": {"name": item.get("name")},
                                            "arguments": item.get("arguments", "{}"),
                                            "id": item.get("call_id")
                                        }
                                        await handle_tool_call(tool_call_data)
                            
                            # Handle tool calls on the backend - check for different tool call event types
                            if data.get("type") == "response.function_call_arguments.done":
                                print(f"🔧 Processing function call: {data.get('name')}")
                                # Create tool call data structure
                                tool_call_data = {
                                    "function": {"name": data.get("name")},
                                    "arguments": data.get("arguments", "{}"),
                                    "id": data.get("call_id")
                                }
                                await handle_tool_call(tool_call_data)
                            elif data.get("type") == "response.tool_calls" and data.get("tool_calls"):
                                print(f"🔧 Processing {len(data['tool_calls'])} tool calls")
                                for tool_call in data["tool_calls"]:
                                    await handle_tool_call(tool_call)
                            else:
                                # Forward other messages to frontend if connection is open
                                if websocket.client_state.name == "CONNECTED":
                                    await websocket.send_text(message)
                                else:
                                    print("⚠️ Frontend disconnected, not forwarding message")
                                    break
                        except json.JSONDecodeError:
                            print(f"⚠️ Invalid JSON from OpenAI: {message}")
                        except Exception as e:
                            print(f"⚠️ Error forwarding to frontend: {e}")
                            break
                            
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 OpenAI connection closed")
                except Exception as e:
                    print(f"⚠️ Forward to frontend error: {e}")
            
            await asyncio.gather(forward_to_openai(), forward_to_frontend())
            
    except Exception as e:
        print(f"❌ WebSocket proxy error: {e}")
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": {"message": str(e)}
                }))
        except Exception as send_error:
            print(f"⚠️ Could not send error message: {send_error}")
    finally:
        try:
            if websocket.client_state.name == "CONNECTED":
                await websocket.close()
        except Exception as close_error:
            print(f"⚠️ Could not close WebSocket: {close_error}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.on_event("startup")
def on_start():
    db.init_db()
    # Only seed if no data exists to avoid database locks
    try:
        # Check if we already have policies
        policies_count = len(db.search_policies(""))
        if policies_count == 0:
            print("🌱 Seeding P&C insurance data...")
            db.seed_customer_policies()
            db.seed_pc_policies()
        else:
            print(f"✅ Database already contains {policies_count} policies - skipping seed")
    except Exception as e:
        print(f"⚠️ Seed check failed: {e}")
        # Try to seed anyway if we can't check
        try:
            db.seed_customer_policies()
            db.seed_pc_policies()
        except Exception as seed_error:
            print(f"❌ Seeding failed: {seed_error}")