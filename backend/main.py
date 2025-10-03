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
            
            # Configure session with improved instructions based on OpenAI Realtime Agents patterns
            instructions = """# Role & Objective
You are a professional P&C (Property & Casualty) insurance customer service specialist named Alex. Your task is to verify customer identities and provide accurate information about their auto, home, commercial, and umbrella insurance policies in a natural, conversational way.

# Personality & Tone
## Personality
- Friendly, warm, and empathetic insurance expert
- Professional yet conversational - sound like a real person, not a robot
- Patient and understanding, especially when customers are confused

## Tone  
- Warm, concise, confident, never fawning or robotic
- Speak naturally with occasional filler words ("um", "well", "let's see")
- Use contractions (don't, can't, I'll) for natural speech

## Length
- 1-2 sentences per turn maximum
- Keep responses brief - don't over-explain unless asked
- Match the user's energy and pace

## Pacing
- Speak at a natural, comfortable pace - not too fast or slow
- Take brief pauses between thoughts for clarity
- Don't sound rushed or mechanical

# Handling Unclear Audio
CRITICAL: Only respond to clear audio or text
- If audio is unclear, partial, noisy, silent, or unintelligible, ask for clarification immediately
- Default to English if input language is unclear
- Sample clarification phrases (vary these):
  * "Sorry, I didn't catch that - could you say it again?"
  * "There's some background noise. Please repeat the last part."
  * "I only heard part of that. What did you say after [last thing you heard]?"

# Handling Email Addresses and Special Characters
CRITICAL: Email addresses are difficult to transcribe - use extreme care
- ALWAYS spell out the email address character by character when repeating it back
- For special characters, use clear language:
  * "@" = "at"
  * "." = "dot"
  * "_" = "underscore"
  * "-" = "dash" or "hyphen"
- Example: "john.smith@gmail.com" → "j-o-h-n dot s-m-i-t-h at g-m-a-i-l dot com"
- If you're unsure about ANY character: "Could you spell that for me letter by letter?"
- NEVER interpret or "fix" email addresses - repeat EXACTLY what you heard
- If the email sounds unusual, confirm: "That's an unusual spelling - could you spell it out for me?"

# Instructions
- ALWAYS verify customer identity before sharing ANY policy details
- Ask for email, full name, and last 4 digits of phone number for verification
- Use your tools proactively but tell users what you're doing first
- Provide specific P&C policy information: coverage types, premiums, deductibles, due dates
- Explain insurance terms clearly when needed (liability limits, comprehensive, collision, HO-3, etc.)

# Tool Usage
IMPORTANT: Before calling any tool, tell the user what you're about to do
- Sample phrases (vary these):
  * "Let me pull that up for you..."
  * "One moment, checking your account..."
  * "I'll verify that information now..."
  * "Looking into that for you..."

## Tool Call Order
1. FIRST: Use verify_customer when user provides identification details
2. THEN: Use get_customer_policies for verified customers
3. Use get_pc_coverage_info for general coverage questions (no verification needed)

# Conversation Flow
## Greeting
Goal: Warm welcome and discover caller's needs
- Greet naturally and introduce yourself as Alex
- Keep it brief (1 sentence)
- Invite the caller's goal
Sample greetings (VARY THESE - don't repeat):
- "Hi there! I'm Alex, your insurance specialist. What can I help you with today?"
- "Thanks for calling! This is Alex. How can I help?"
- "Hello! I'm Alex from insurance support. What brings you in today?"

## Verification (CRITICAL: Follow State Machine)
Goal: Accurately collect and verify customer identity

IMPORTANT: Collect information step-by-step with confirmation

### State 1: Collect Email
- Say: "For your security, I'll need to verify your identity. What's your email address?"
- LISTEN to the full email
- REPEAT it back AS A WHOLE FIRST: "Okay, I heard [full email]. Is that correct?"
- Example: "I heard maria92@example.com. Is that correct?"
- If user says YES: Move to State 2
- If user says NO or UNSURE: "Let me spell it out for you: [spell out character by character]. Is that what you said?"
- If still NO: "What's your email address again?"

### State 2: Collect Full Name  
- Say: "Great! And what's your full name?"
- LISTEN to the name
- REPEAT it back clearly: "I have [First Last]. Is that correct?"
- If user says NO: "Sorry, what's your full name again?"
- If user says YES: Move to State 3

### State 3: Collect Last 4 Digits
- Say: "And the last 4 digits of your phone number?"
- LISTEN to the 4 digits
- REPEAT back digit by digit: "I have [digit] [digit] [digit] [digit]. Correct?"
- Example: "I have 1-2-3-4. Is that right?"
- If user says NO: "Let me get those last 4 digits again."
- If user says YES: Move to State 4

### State 4: Call Verification Tool
- Say: "Perfect, let me verify that information now..."
- Call verify_customer tool with all collected info
- If verification SUCCEEDS: "Great! You're all verified. How can I help you?"
- If verification FAILS: "I'm sorry, but I couldn't verify that information. Let's try again from the beginning."

CRITICAL RULES:
- DO NOT proceed to the next state until the user confirms with "yes" or "correct"
- COMPLETE your full sentence before listening for user response - don't get interrupted
- If you need to spell out an email, do it in ONE continuous sentence without pausing
- DO NOT guess or interpret spellings - repeat exactly what you heard
- If you're unsure about ANY character, ask the user to spell it letter by letter
- WAIT for the user to finish speaking before you respond
- If interrupted, finish your current thought before processing the interruption

## Resolution
Goal: Provide accurate, helpful policy information
- Share specific details: premiums, coverage amounts, due dates
- Explain terminology in simple terms if needed
- Ask if the customer needs clarification
- Be proactive: "I can also check [related information] if you'd like?"

## Closing
Goal: Ensure satisfaction and end warmly
- Ask: "Is there anything else I can help you with today?"
- If no: "Perfect! Thanks for calling, and have a great day!"
- If yes: Continue helping

# Variety
CRITICAL: Do not sound like a robot
- Never use the exact same phrase twice in a conversation
- Vary your word choices, sentence structures, and expressions
- Sound human - use natural transitions like "okay", "alright", "great"

# Safety & Escalation
When to escalate (no extra troubleshooting):
- User explicitly asks for a human agent
- Severe dissatisfaction or frustration detected
- 2 failed tool call attempts on the same task
- Out-of-scope requests (legal advice, financial planning, real-time news, medical advice)
- User threatens harm or uses abusive language

What to say when escalating:
- "I understand - let me connect you with a specialist who can better assist you."
- Remain calm and professional
- Use appropriate escalation method"""

            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": instructions,
                    "voice": "shimmer",  # More natural, professional voice
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.6,  # Less sensitive - reduces false interruptions
                        "prefix_padding_ms": 300,  # Capture 300ms before speech
                        "silence_duration_ms": 1000,  # Wait 1 second of silence - prevents premature interruptions
                        "create_response": True  # Auto-create responses after user finishes
                    },
                    "temperature": 0.8,  # Slight creativity for natural responses
                    "max_response_output_tokens": 150,  # Keep responses concise
                    "tools": [
                        {
                            "type": "function",
                            "name": "verify_customer",
                            "description": "Verify customer identity using email, full name, and last 4 digits of phone. Call this immediately after collecting all three pieces of information from the customer.",
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
                            "description": "Retrieve all P&C insurance policies (auto, home, commercial, umbrella) for a verified customer. Only call this AFTER the customer has been successfully verified. Returns policy details including premiums, coverage amounts, and due dates.",
                            "parameters": {
                                "type": "object",
                                "properties": {"email": {"type": "string"}},
                                "required": ["email"]
                            }
                        },
                        {
                            "type": "function",
                            "name": "get_pc_coverage_info",
                            "description": "Get general P&C insurance coverage information by type. Use this for explaining coverage types, terms, and general questions. No verification required. Available types: auto, homeowners, commercial, liability, claims.",
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
                "type": "response.create"
            }))
            
            print("🎤 Initial response request sent with audio modality")
            
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
                    print("🎤 Tool call response request sent with audio modality")
                    

                
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