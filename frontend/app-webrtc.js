// ===== WebRTC-based Realtime API Implementation =====
// This provides lower latency and better audio quality than WebSocket

// ===== Elements =====
const statusEl = document.getElementById("status");
const statusDot = document.getElementById("statusDot");
const transcriptEl = document.getElementById("transcript");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const connectionStatus = document.getElementById("connectionStatus");

const vEmail = document.getElementById("vEmail");
const vName = document.getElementById("vName");
const vLast4 = document.getElementById("vLast4");
const vOrder = document.getElementById("vOrder");
const verifyBtn = document.getElementById("verifyBtn");
const verifyStatus = document.getElementById("verifyStatus");
const verifyStatusBadge = document.getElementById("verifyStatusBadge");

const refreshPolicies = document.getElementById("refreshPolicies");
const policyList = document.getElementById("policyList");
const demoBtn = document.getElementById("demoBtn");

// ===== State =====
let peerConnection = null;
let dataChannel = null;
let audioElement = null;
let verified = false;
const sessionId = crypto.randomUUID();

// keep separate partial bubbles so agent/user don't overwrite each other
let partialAgentEl = null;
let partialUserEl = null;

// ===== UI helpers =====
function makeBubble({ who, text, partial = false }) {
  const row = document.createElement("div");
  row.className = "flex gap-3 mb-4 animate-fadeIn " + 
    (who === "agent" ? "justify-start" : who === "you" ? "justify-end" : "justify-center");

  // Create avatar
  if (who === "agent" || who === "you") {
    const avatar = document.createElement("div");
    avatar.className = "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-lg " + 
      (who === "agent" 
        ? "bg-gradient-to-br from-blue-500 to-purple-600" 
        : "bg-gradient-to-br from-emerald-500 to-teal-600");
    avatar.textContent = who === "agent" ? "🤖" : "👤";
    
    if (who === "agent") {
      row.appendChild(avatar);
    }
  }

  // Create message container
  const messageContainer = document.createElement("div");
  messageContainer.className = "flex flex-col max-w-md " + (who === "you" ? "items-end" : "items-start");

  // Create name label
  if (who !== "system") {
    const nameLabel = document.createElement("div");
    nameLabel.className = "text-xs font-semibold mb-1.5 px-1 " + 
      (who === "agent" ? "text-blue-600" : "text-emerald-600");
    nameLabel.textContent = who === "agent" ? "Alex (AI Agent)" : "You";
    messageContainer.appendChild(nameLabel);
  }

  // Create bubble
  const bubble = document.createElement("div");
  bubble.className =
    "px-4 py-3 rounded-2xl shadow-lg text-sm leading-relaxed " +
    (who === "agent"
      ? "bg-gradient-to-br from-blue-50 to-indigo-50 text-slate-800 border-2 border-blue-200"
      : who === "you"
      ? "bg-gradient-to-br from-emerald-50 to-teal-50 text-slate-800 border-2 border-emerald-200"
      : "bg-gradient-to-br from-amber-50 to-orange-50 text-amber-900 border-2 border-amber-300 text-xs");

  if (partial) {
    bubble.classList.add("opacity-80");
    const textSpan = document.createElement("span");
    textSpan.textContent = text || "";
    const dots = document.createElement("span");
    dots.className = "inline-block ml-1 animate-pulse font-bold";
    dots.textContent = "●●●";
    bubble.appendChild(textSpan);
    bubble.appendChild(dots);
  } else {
    bubble.textContent = text;
  }

  messageContainer.appendChild(bubble);
  row.appendChild(messageContainer);

  // Add avatar for user on the right
  if (who === "you") {
    const avatar = document.createElement("div");
    avatar.className = "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-lg bg-gradient-to-br from-emerald-500 to-teal-600";
    avatar.textContent = "👤";
    row.appendChild(avatar);
  }

  transcriptEl.appendChild(row);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;

  if (partial) {
    if (who === "agent") partialAgentEl = bubble;
    else partialUserEl = bubble;
  }

  return bubble;
}

function setStatus(text, dotClass = "") {
  statusEl.textContent = text;
  if (dotClass) {
    statusDot.className = "h-2.5 w-2.5 rounded-full " + dotClass;
  }
}

// Helper to extract and populate form fields from conversation
function tryPopulateFormFromTranscript(text) {
  const lowerText = text.toLowerCase();
  
  // Try to extract email (pattern: word@word.word)
  const emailMatch = text.match(/[\w\.-]+@[\w\.-]+\.\w+/i);
  if (emailMatch && !vEmail.value) {
    vEmail.value = emailMatch[0].toLowerCase();
    vEmail.classList.add('bg-yellow-100', 'border-yellow-400');
    setTimeout(() => {
      vEmail.classList.remove('bg-yellow-100', 'border-yellow-400');
    }, 2000);
    console.log("📝 Auto-populated email:", vEmail.value);
  }
  
  // Try to extract last 4 digits (pattern: 4 consecutive digits)
  if (lowerText.includes("last 4") || lowerText.includes("last four")) {
    const digitsMatch = text.match(/\b\d{4}\b/);
    if (digitsMatch && !vLast4.value) {
      vLast4.value = digitsMatch[0];
      vLast4.classList.add('bg-yellow-100', 'border-yellow-400');
      setTimeout(() => {
        vLast4.classList.remove('bg-yellow-100', 'border-yellow-400');
      }, 2000);
      console.log("📝 Auto-populated last4:", vLast4.value);
    }
  }
}

// Helper to highlight form field when updated
function highlightField(field) {
  field.classList.add('bg-blue-100', 'border-blue-400');
  setTimeout(() => {
    field.classList.remove('bg-blue-100', 'border-blue-400');
  }, 2000);
}

// ===== WebRTC Connection =====
async function startCall() {
  try {
    setStatus("connecting", "bg-yellow-500");
    console.log("🚀 Starting WebRTC Realtime connection...");

    // Get ephemeral token from backend
    console.log("🔑 Fetching ephemeral token...");
    const tokenResponse = await fetch("/api/realtime/token");
    if (!tokenResponse.ok) {
      const errorText = await tokenResponse.text();
      console.error("❌ Token fetch failed:", tokenResponse.status, errorText);
      throw new Error(`Token fetch failed (${tokenResponse.status}): ${errorText}`);
    }
    const tokenData = await tokenResponse.json();
    const EPHEMERAL_KEY = tokenData.client_secret;
    
    if (!EPHEMERAL_KEY) {
      throw new Error("No client_secret received from backend");
    }
    
    console.log("✅ Got ephemeral token (expires at:", tokenData.expires_at, ")");
    console.log("✅ Got ephemeral token");

    // Create peer connection
    peerConnection = new RTCPeerConnection();

    // Set up remote audio playback
    audioElement = document.createElement("audio");
    audioElement.autoplay = true;
    peerConnection.ontrack = (e) => {
      console.log("🔊 Received remote audio track");
      audioElement.srcObject = e.streams[0];
    };

    // Add local audio track for microphone
    console.log("🎤 Requesting microphone access...");
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 24000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    peerConnection.addTrack(stream.getTracks()[0]);
    console.log("✅ Microphone added to peer connection");

    // Set up data channel for events
    dataChannel = peerConnection.createDataChannel("oai-events");
    
    dataChannel.onopen = () => {
      console.log("✅ Data channel opened");
      
      // Configure session with instructions and tools
      const sessionConfig = {
        type: "session.update",
        session: {
          modalities: ["text", "audio"],
          instructions: `# LANGUAGE REQUIREMENT
CRITICAL: You MUST speak ONLY in ENGLISH at ALL times. NEVER use Spanish, French, or any other language. If the user speaks another language, respond ONLY in English.

# Role
You are Alex, a professional P&C (Property & Casualty) insurance customer service specialist. Your goal is to verify customer identities and provide accurate information about their auto, home, commercial, and umbrella insurance policies.

# Personality & Tone
- Warm, friendly, and professional
- Speak naturally with contractions (don't, can't, I'll)
- Keep responses brief: 1-2 sentences maximum
- Sound like a real person, not a robot

# Name Spelling Note
IMPORTANT: Accept phonetic variations of names. For example, "Gray" and "Grey" are the same name - accept either spelling.

# Verification Flow - State Machine
You MUST follow this exact sequence:

### State 1: Collect Email
- Say: "Hi! I'm Alex. What's your email address?"
- LISTEN to the email
- SPELL it back character by character: "I have [spell each char]. Is that correct?"
- Example: "I have j-o-h-n dot s-m-i-t-h at g-m-a-i-l dot com. Is that right?"
- If user says NO: "Let me get that again. What's your email?"
- If user says YES: Move to State 2

### State 2: Collect Full Name
- Say: "Great! And what's your full name?"
- LISTEN to the name
- REPEAT it back: "I have [First Last]. Is that correct?"
- If user says YES: Move to State 3

### State 3: Collect Last 4 Digits
- Say: "And the last 4 digits of your phone number?"
- LISTEN to the 4 digits
- REPEAT back digit by digit: "I have [digit] [digit] [digit] [digit]. Correct?"
- If user says YES: Move to State 4

### State 4: Call Verification Tool
- Say: "Perfect, let me verify that information..."
- Call verify_customer tool with all collected info
- If VERIFIED: "Great! You're all verified. How can I help you today?"
- If FAILED: "I couldn't verify that information. Let's try again."

# Email Handling Rules
CRITICAL: Email addresses are difficult to transcribe
- ALWAYS spell emails character by character when repeating back
- "@" = "at", "." = "dot", "_" = "underscore", "-" = "dash"
- Example: "john.smith@gmail.com" → "j-o-h-n dot s-m-i-t-h at g-m-a-i-l dot com"
- If unsure about ANY character, ask user to spell it

# After Verification
Once verified, you can:
- Call get_customer_policies to retrieve their P&C insurance policies
- Call get_pc_coverage_info to explain coverage types
- Answer questions about auto, home, commercial, and umbrella insurance
- Explain premiums, deductibles, coverage limits, and policy terms

# Important Rules
- ONLY speak English (never Spanish or other languages)
- Complete your full sentence before pausing
- Don't interrupt yourself mid-sentence
- Wait for user confirmation before moving to next state
- Be patient and natural`,
          voice: "shimmer",
          input_audio_format: "pcm16",
          output_audio_format: "pcm16",
          input_audio_transcription: {
            model: "whisper-1"
          },
          turn_detection: {
            type: "server_vad",
            threshold: 0.5,  // Optimized from OpenAI Agents repo
            prefix_padding_ms: 300,
            silence_duration_ms: 700,  // Reduced for better responsiveness
            create_response: true
          },
          temperature: 0.7,  // Slightly lower for more consistent responses
          max_response_output_tokens: 800,  // Allow longer responses for detailed policy information
          tools: [
            {
              type: "function",
              name: "verify_customer",
              description: "Verify customer identity by checking email, full name, and last 4 digits of phone number. MUST be called after collecting all three pieces of information and getting user confirmation. Returns {verified: true/false}.",
              parameters: {
                type: "object",
                properties: {
                  email: { 
                    type: "string",
                    description: "Customer's email address (confirmed by spelling out)" 
                  },
                  full_name: { 
                    type: "string",
                    description: "Customer's full name (confirmed by user)" 
                  },
                  last4: { 
                    type: "string",
                    description: "Last 4 digits of phone number (confirmed digit by digit)" 
                  }
                },
                required: ["email", "full_name", "last4"]
              }
            },
            {
              type: "function",
              name: "get_customer_policies",
              description: "Retrieve all P&C insurance policies (auto, homeowners, commercial, umbrella) for a verified customer. Only call AFTER customer is successfully verified. Returns array of policy objects with details like policy numbers, premiums, coverage amounts, and renewal dates.",
              parameters: {
                type: "object",
                properties: {
                  email: { 
                    type: "string",
                    description: "Verified customer's email address" 
                  }
                },
                required: ["email"]
              }
            },
            {
              type: "function",
              name: "get_pc_coverage_info",
              description: "Get general P&C insurance coverage information and explanations. Use this to answer questions about coverage types, terms, limits, and general insurance concepts. No verification required for public information.",
              parameters: {
                type: "object",
                properties: {
                  coverage_type: { 
                    type: "string",
                    enum: ["auto", "homeowners", "commercial", "liability", "claims"],
                    description: "Type of coverage to get information about: 'auto' for vehicle insurance, 'homeowners' for property insurance, 'commercial' for business insurance, 'liability' for liability coverage, 'claims' for claims process"
                  }
                },
                required: ["coverage_type"]
              }
            }
          ]
        }
      };

      console.log("📤 Sending session configuration with tools...");
      dataChannel.send(JSON.stringify(sessionConfig));
      
      // Request initial greeting
      setTimeout(() => {
        console.log("📤 Requesting initial greeting...");
        dataChannel.send(JSON.stringify({ type: "response.create" }));
      }, 100);
      
      setStatus("connected", "bg-emerald-500");
      connectionStatus.textContent = "Connected via WebRTC ⚡";
      makeBubble({ who: "system", text: "🎉 Connected! Configuring AI agent..." });
    };

    dataChannel.onmessage = (e) => {
      const event = JSON.parse(e.data);
      handleRealtimeEvent(event);
    };

    dataChannel.onclose = () => {
      console.log("🔌 Data channel closed");
      stopCall();
    };

    // Create offer and set local description
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    console.log("📤 Created SDP offer");

    // Send offer to OpenAI Realtime API (WebRTC endpoint)
    console.log("📤 Sending SDP offer to OpenAI Realtime...");
    console.log("🔑 Using ephemeral token");
    
    const sdpResponse = await fetch("https://api.openai.com/v1/realtime", {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${EPHEMERAL_KEY}`,
        "Content-Type": "application/sdp"
      },
    });

    if (!sdpResponse.ok) {
      const errorText = await sdpResponse.text();
      console.error("❌ SDP exchange failed:", sdpResponse.status, errorText);
      console.error("❌ Full error details:", errorText);
      throw new Error(`SDP exchange failed (${sdpResponse.status}): ${errorText}`);
    }

    const answerSdp = await sdpResponse.text();
    const answer = {
      type: "answer",
      sdp: answerSdp,
    };
    await peerConnection.setRemoteDescription(answer);
    console.log("✅ WebRTC connection established");

  } catch (error) {
    console.error("❌ WebRTC connection error:", error);
    setStatus("error", "bg-red-500");
    makeBubble({ who: "system", text: `❌ Connection failed: ${error.message}` });
  }
}

function stopCall() {
  console.log("🔌 Closing WebRTC connection...");
  
  if (dataChannel) {
    dataChannel.close();
    dataChannel = null;
  }
  
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  
  if (audioElement) {
    audioElement.srcObject = null;
    audioElement = null;
  }
  
  setStatus("idle", "bg-slate-300");
  connectionStatus.textContent = "Not connected";
  console.log("✅ Disconnected");
}

// ===== Event Handling =====
function handleRealtimeEvent(evt) {
  console.log("📨 Received event:", evt.type, evt);

  // Handle transcript updates
  if (evt.type === "conversation.item.input_audio_transcription.completed") {
    const text = evt.transcript || "(audio)";
    
    // Try to auto-populate form fields from user speech
    tryPopulateFormFromTranscript(text);
    
    if (partialUserEl) {
      partialUserEl.textContent = text;
      partialUserEl = null;
    } else {
      makeBubble({ who: "you", text });
    }
    return;
  }

  // Handle assistant text responses (WebRTC uses audio_transcript, not text)
  if (evt.type === "response.text.delta" && typeof evt.delta === "string") {
    if (!partialAgentEl) {
      partialAgentEl = makeBubble({ who: "agent", text: evt.delta, partial: true });
    } else {
      partialAgentEl.textContent += evt.delta;
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }
    return;
  }

  if (evt.type === "response.text.done") {
    partialAgentEl = null;
    return;
  }

  // Handle assistant AUDIO TRANSCRIPT (this is what WebRTC uses!)
  if (evt.type === "response.audio_transcript.delta") {
    const delta = evt.delta || "";
    if (!partialAgentEl) {
      partialAgentEl = makeBubble({ who: "agent", text: delta, partial: true });
    } else {
      // Update the text content (removing the typing indicator first)
      const currentText = partialAgentEl.querySelector('span:first-child')?.textContent || partialAgentEl.textContent;
      const cleanText = currentText.replace(/●●●$/, ''); // Remove old typing indicator
      partialAgentEl.innerHTML = `<span>${cleanText}${delta}</span><span class="inline-block ml-1 animate-pulse font-bold">●●●</span>`;
      transcriptEl.scrollTop = transcriptEl.scrollHeight;
    }
    return;
  }

  if (evt.type === "response.audio_transcript.done") {
    if (partialAgentEl) {
      // Finalize the message - remove typing indicator
      const finalText = evt.transcript || partialAgentEl.textContent.replace(/●●●$/, '').trim();
      partialAgentEl.textContent = finalText;
      partialAgentEl.classList.remove('opacity-80', 'animate-pulse');
      console.log("✅ AI message complete:", finalText);
      partialAgentEl = null;
    }
    return;
  }

  // Check if response was incomplete/truncated (merged handler - removed duplicate below)
  if (evt.type === "response.done") {
    console.log("✅ Response completed", evt.response);
    
    // Check for incomplete response (token limit reached)
    if (evt.response?.status === "incomplete") {
      console.warn("⚠️ Response incomplete - reason:", evt.response.status_details?.reason);
      if (evt.response.status_details?.reason === "max_tokens") {
        makeBubble({ who: "system", text: "⚠️ Response was truncated due to length limit. Increasing token limit..." });
      }
    }
    
    // Check for failed response
    if (evt.response?.status === "failed") {
      console.error("❌ Response failed:", evt.response.status_details);
      if (evt.response.status_details && evt.response.status_details.error) {
        const error = evt.response.status_details.error;
        makeBubble({ 
          who: "system", 
          text: `❌ Error: ${error.message || "Response failed"}` 
        });
        
        // Check for quota error
        if (error.code === "insufficient_quota") {
          makeBubble({ 
            who: "system", 
            text: "⚠️ Insufficient quota. Please add credits to your OpenAI account at https://platform.openai.com/settings/organization/billing" 
          });
        }
      }
    }
    return;
  }

  // Handle assistant audio - WebRTC handles playback automatically
  if (evt.type === "response.audio.delta") {
    // Audio is played automatically by WebRTC, no action needed
    return;
  }

  // Handle session updates
  if (evt.type === "session.updated") {
    console.log("✅ Session updated");
    return;
  }

  // Handle errors
  if (evt.type === "error") {
    console.error("❌ OpenAI Error:", evt.error);
    makeBubble({ who: "system", text: `❌ Error: ${evt.error.message || "Unknown error"}` });
    return;
  }

  // Handle speech detection
  if (evt.type === "input_audio_buffer.speech_started") {
    console.log("🎤 User speech detected");
    if (!partialUserEl) {
      partialUserEl = makeBubble({ who: "you", text: "...", partial: true });
    }
    return;
  }

  if (evt.type === "input_audio_buffer.speech_stopped") {
    console.log("🔇 User speech ended");
    return;
  }

  // Handle tool calls
  if (evt.type === "response.function_call_arguments.done") {
    console.log("🔧 Tool call detected:", evt);
    handleToolCall(evt);
    return;
  }
}

// ===== Tool Call Handling =====
async function handleToolCall(evt) {
  const toolName = evt.name;
  const callId = evt.call_id;
  let args = {};
  
  try {
    args = JSON.parse(evt.arguments);
  } catch (e) {
    console.error("❌ Failed to parse tool arguments:", e);
    return;
  }

  console.log(`🔧 Tool call: ${toolName}`, args);

  try {
    let result;
    
    if (toolName === "verify_customer") {
      console.log("🔍 Verifying customer - AI args:", args);
      
      // Update form fields with AI's values if form is empty
      // This lets the user see what the AI heard
      if (!vEmail.value && args.email) {
        vEmail.value = args.email;
        highlightField(vEmail);
      }
      if (!vName.value && args.full_name) {
        vName.value = args.full_name;
        highlightField(vName);
      }
      if (!vLast4.value && args.last4) {
        vLast4.value = args.last4;
        highlightField(vLast4);
      }
      if (!vOrder.value && args.order_id) {
        vOrder.value = args.order_id;
        highlightField(vOrder);
      }
      
      // IMPORTANT: Always use form values for verification (they're what user confirmed)
      const verifyData = {
        email: vEmail.value,
        full_name: vName.value,
        last4: vLast4.value,
        order_id: vOrder.value
      };
      
      console.log("📤 Sending verification with form values:", verifyData);
      
      // Call backend API to verify customer - with session tracking
      const response = await fetch("/api/verify", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-Session-Id": sessionId  // Pass session ID for tracking
        },
        body: JSON.stringify(verifyData)
      });
      result = await response.json();
      
      // Update local verification state
      verified = !!result.verified;
      
      // Update verification status badge
      verifyStatusBadge.textContent = verified ? "Verified" : "Not verified";
      verifyStatusBadge.className =
        "text-xs px-2 py-1 rounded-full " +
        (verified ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600");
      
      makeBubble({ who: "system", text: verified ? "✅ Customer verified!" : "❌ Verification failed" });
      console.log("✅ Verification result:", result);
      console.log("📝 Session ID:", sessionId, "Verified:", verified);
      
    } else if (toolName === "get_customer_policies") {
      console.log("📋 Fetching customer policies:", args);
      console.log("📝 Using session ID:", sessionId, "Verified status:", verified);
      
      // Check if customer is verified first
      if (!verified) {
        console.warn("⚠️ Attempting to get policies without verification!");
        result = { 
          error: "verification_required", 
          message: "Customer must be verified before accessing policy information",
          policies: []
        };
        makeBubble({ who: "system", text: "⚠️ Verification required to access policies" });
      } else {
        // Call backend API to get policies - correct endpoint
        const response = await fetch(`/api/customer/${encodeURIComponent(args.email)}/policies`, {
          headers: { "X-Session-Id": sessionId }
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error("❌ Policies fetch failed:", response.status, errorText);
          result = { 
            error: "Failed to fetch policies", 
            message: response.status === 403 ? "Session not verified on backend" : `HTTP ${response.status}`,
            policies: []
          };
          makeBubble({ who: "system", text: `❌ Could not fetch policies (${response.status})` });
        } else {
          result = await response.json();
          const policies = Array.isArray(result) ? result : [];
          const count = policies.length;
          
          // Format result for AI
          result = { policies, count };
          
          makeBubble({ who: "system", text: `📋 Found ${count} P&C insurance ${count === 1 ? 'policy' : 'policies'}` });
          console.log("✅ Policies fetched:", result);
        }
      }
      
    } else if (toolName === "get_pc_coverage_info") {
      console.log("📚 Fetching coverage info:", args);
      
      // Call backend API to get coverage info - correct endpoint
      const response = await fetch(`/api/pc-coverage/${args.coverage_type}`, {
        headers: { "X-Session-Id": sessionId }
      });
      
      if (!response.ok) {
        result = { error: "Coverage information not found" };
      } else {
        result = await response.json();
        makeBubble({ who: "system", text: `📚 ${args.coverage_type} coverage information retrieved` });
        console.log("✅ Coverage info fetched:", result);
      }
      
    } else {
      console.error("❌ Unknown tool:", toolName);
      result = { error: `Unknown tool: ${toolName}` };
    }

    // Send tool result back to OpenAI via data channel
    console.log("📤 Sending tool result to OpenAI");
    sendEvent({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: callId,
        output: JSON.stringify(result)
      }
    });

    // Request AI to respond with the tool result
    sendEvent({
      type: "response.create"
    });

  } catch (error) {
    console.error("❌ Tool call error:", error);
    makeBubble({ who: "system", text: `❌ Tool error: ${error.message}` });
    
    // Send error back to OpenAI
    sendEvent({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: callId,
        output: JSON.stringify({ error: error.message })
      }
    });
    
    sendEvent({
      type: "response.create"
    });
  }
}

function sendEvent(event) {
  if (dataChannel && dataChannel.readyState === "open") {
    dataChannel.send(JSON.stringify(event));
    console.log("📤 Sent event:", event.type);
  } else {
    console.error("❌ Data channel not open");
  }
}

// ===== Wire buttons =====
connectBtn.addEventListener("click", startCall);
disconnectBtn.addEventListener("click", stopCall);

// Demo button functionality
demoBtn.addEventListener("click", () => {
  vEmail.value = "maria92@example.com";
  vName.value = "Heather Gray";  // Note: Database has "Gray" not "Grey"
  vLast4.value = "1234";
  vOrder.value = "POLICY-1632-Re";
  makeBubble({ who: "you", text: "📝 Demo data loaded! Customer: Heather Gray (with 'a' not 'e')" });
});

// Activate Audio button
document.getElementById("activateAudioBtn")?.addEventListener("click", async () => {
  console.log("🔊 Audio activation requested (not needed for WebRTC)");
  makeBubble({ who: "system", text: "🔊 WebRTC handles audio automatically! Just click Connect." });
});

// Initial status
setStatus("idle", "bg-slate-300");
connectionStatus.textContent = "Not connected";
console.log("✅ WebRTC app loaded. Ready to connect!");

