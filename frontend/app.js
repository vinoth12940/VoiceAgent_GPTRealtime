// ===== Elements =====
const statusEl = document.getElementById("status");
const statusDot = document.getElementById("statusDot");
const transcriptEl = document.getElementById("transcript");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const remoteAudio = document.getElementById("remoteAudio");
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
let websocket = null;
let verified = false;
const sessionId = crypto.randomUUID();

// keep separate partial bubbles so agent/user don't overwrite each other
let partialAgentEl = null;
let partialUserEl = null;

// Audio handling
let audioContext = null;
let audioQueue = [];
let isPlaying = false;

// Microphone handling
let mediaStream = null;
let mediaRecorder = null;
let isRecording = false;
let recordingChunks = [];

// Voice Activity Detection - simplified
let audioProcessor = null;
let isListening = false;

// ===== UI helpers (pure Tailwind bubbles) =====
function makeBubble({ who, text, partial = false }) {
  const row = document.createElement("div");
  row.className = "flex " + (who === "agent" ? "justify-start" : "justify-end");

  const bubble = document.createElement("div");
  bubble.className =
    "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow " +
    (who === "agent"
      ? "bg-blue-50 text-slate-800 border border-blue-100"
      : "bg-emerald-50 text-slate-800 border border-emerald-100");

  if (partial) {
    bubble.classList.add("opacity-70");
    bubble.innerHTML = `<span class="inline-block align-middle mr-2">${escapeHtml(
      text || ""
    )}</span><span class="inline-block align-middle animate-pulse">•••</span>`;
  } else {
    bubble.textContent = text;
  }

  row.appendChild(bubble);
  transcriptEl.appendChild(row);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;

  return bubble;
}

function setStatus(label, color) {
  statusEl.textContent = label;
  statusDot.className = `h-2.5 w-2.5 rounded-full ${color}`;
  
  // Update connection status
  if (connectionStatus) {
    connectionStatus.textContent = label;
    connectionStatus.className = `font-medium ${color === 'bg-emerald-500' ? 'text-emerald-600' : 
      color === 'bg-rose-500' ? 'text-rose-600' : 
      color === 'bg-amber-400' ? 'text-amber-600' : 'text-slate-500'}`;
  }
}

function escapeHtml(str) {
  return (str || "").replace(/[&<>'"]/g, s => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[s]));
}

// ----- Agent partial handling -----
function updateAgentPartial(text) {
  if (!partialAgentEl) {
    partialAgentEl = makeBubble({ who: "agent", text, partial: true });
  } else {
    partialAgentEl.innerHTML = `<span class="inline-block align-middle mr-2">${escapeHtml(
      text
    )}</span><span class="inline-block align-middle animate-pulse">•••</span>`;
  }
}

function finalizeAgentPartial(finalText) {
  if (partialAgentEl) {
    partialAgentEl.classList.remove("opacity-70");
    partialAgentEl.textContent = finalText;
    partialAgentEl = null;
  } else if (finalText) {
    makeBubble({ who: "agent", text: finalText });
  }
}

// ----- User partial handling -----
function updateUserPartial(text) {
  if (!partialUserEl) {
    partialUserEl = makeBubble({ who: "you", text, partial: true });
  } else {
    partialUserEl.innerHTML = `<span class="inline-block align-middle mr-2">${escapeHtml(
      text
    )}</span><span class="inline-block align-middle animate-pulse">•••</span>`;
  }
}

function finalizeUserPartial(finalText) {
  if (partialUserEl) {
    partialUserEl.classList.remove("opacity-70");
    partialUserEl.textContent = finalText;
    partialUserEl = null;
  } else if (finalText) {
    makeBubble({ who: "you", text: finalText });
  }
}

function clearTranscript() {
  transcriptEl.innerHTML = `
    <div class="text-center text-slate-400 text-sm py-8">
      <div class="mb-2">🎤</div>
      <div>Click "Connect" to start your conversation</div>
      <div class="text-xs mt-1">The AI will help you with policies and customer verification</div>
    </div>
  `;
}

// ===== Audio handling =====
async function initAudioContext() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    console.log("🔊 Audio context created, state:", audioContext.state);
  }
  
  if (audioContext.state === 'suspended') {
    console.log("🔊 Resuming suspended audio context...");
    await audioContext.resume();
    console.log("🔊 Audio context resumed, state:", audioContext.state);
  }
}

// ===== Microphone handling with VAD =====
async function initMicrophone() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 24000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    
    console.log("🎤 Microphone initialized");
    
    // Initialize audio context for direct audio processing
    await initAudioContext();
    
    // Create an audio source from the media stream
    const source = audioContext.createMediaStreamSource(mediaStream);
    
    // Create a script processor for real-time audio processing
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (event) => {
      const inputBuffer = event.inputBuffer;
      const inputData = inputBuffer.getChannelData(0);
      
      // Convert to PCM16 and send to OpenAI
      sendRawAudioToOpenAI(inputData);
    };
    
    // Connect the audio processing chain
    source.connect(processor);
    processor.connect(audioContext.destination);
    
    // Store reference for cleanup
    audioProcessor = processor;
    
    console.log("🎤 Real-time audio processing started");
    return true;
  } catch (error) {
    console.error("❌ Could not initialize microphone:", error);
    makeBubble({ who: "agent", text: "❌ Could not access microphone. Please check permissions." });
    return false;
  }
}

// Simplified VAD - rely on OpenAI's server-side VAD instead
async function setupVAD() {
  isListening = true;
  console.log("👂 Using OpenAI server-side Voice Activity Detection");
}

// Send raw audio data to OpenAI Realtime API (no encoding issues)
function sendRawAudioToOpenAI(float32Data) {
  try {
    // Convert Float32 directly to PCM16 (no resampling needed - already 24kHz)
    const pcm16 = new Int16Array(float32Data.length);
    
    for (let i = 0; i < float32Data.length; i++) {
      // Clamp and convert to 16-bit PCM
      const sample = Math.max(-1, Math.min(1, float32Data[i]));
      pcm16[i] = Math.floor(sample * 32767);
    }
    
    // Convert to base64
    const bytes = new Uint8Array(pcm16.buffer);
    const base64Audio = btoa(String.fromCharCode.apply(null, bytes));
    
    // Send audio input event to OpenAI - let server-side VAD handle timing
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      sendMessage({
        type: "input_audio_buffer.append",
        audio: base64Audio
      });
      
      console.log("🎤 Raw audio chunk sent to OpenAI, samples:", float32Data.length, "base64 length:", base64Audio.length);
    }
  } catch (error) {
    console.error("❌ Error sending raw audio:", error);
  }
}

function startRecording() {
  if (!audioProcessor || isRecording) return;
  
  isRecording = true;
  console.log("🎤 Audio streaming started");
  
  // Visual feedback
  setStatus("listening", "bg-red-500");
  // Audio processing is already running via the script processor
}

function stopRecording() {
  if (!audioProcessor || !isRecording) return;
  
  isRecording = false;
  console.log("🎤 Audio streaming stopped");
  
  // Visual feedback
  setStatus("processing", "bg-amber-400");
  // Audio processing continues but we can add logic here if needed
}

// Simplified - OpenAI handles audio processing with server-side VAD
// No need for manual audio conversion

function playAudioDelta(audioData) {
  try {
    // audioData is base64 encoded PCM16 audio
    const binaryString = atob(audioData);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Convert to Int16Array (PCM16)
    const pcm16 = new Int16Array(bytes.buffer);
    
    // Queue the audio for playback
    audioQueue.push(pcm16);
    
    if (!isPlaying) {
      playNextAudio();
    }
  } catch (error) {
    console.error("Error playing audio delta:", error);
  }
}

async function playNextAudio() {
  if (audioQueue.length === 0) {
    isPlaying = false;
    return;
  }
  
  isPlaying = true;
  
  try {
    await initAudioContext();
    
    const pcm16Data = audioQueue.shift();
    
    // Create audio buffer
    const audioBuffer = audioContext.createBuffer(1, pcm16Data.length, 24000); // 24kHz sample rate
    const channelData = audioBuffer.getChannelData(0);
    
    // Convert PCM16 to float32
    for (let i = 0; i < pcm16Data.length; i++) {
      channelData[i] = pcm16Data[i] / 32768.0; // Convert to -1.0 to 1.0 range
    }
    
    // Create and play audio source
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    
    source.onended = () => {
      setTimeout(playNextAudio, 10); // Small delay to prevent audio glitches
    };
    
    source.start();
    
  } catch (error) {
    console.error("Error playing audio:", error);
    isPlaying = false;
    // Try to continue with next audio
    setTimeout(playNextAudio, 100);
  }
}

// ===== Backend helper =====
async function callBackend(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json", "X-Session-Id": sessionId };
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ===== Verification =====
verifyBtn.addEventListener("click", async () => {
  verifyStatus.textContent = "Submitting…";
  try {
    const payload = {
      email: vEmail.value.trim(),
      full_name: vName.value.trim(),
      last4: vLast4.value.trim(),
      order_id: vOrder.value.trim()
    };
    const result = await callBackend("/verify", "POST", payload);
    verified = !!result.verified;
    verifyStatus.textContent = verified ? "✅ Verified" : "❌ Not verified";
    verifyStatusBadge.textContent = verified ? "Verified" : "Not verified";
    verifyStatusBadge.className =
      "text-xs px-2 py-1 rounded-full " +
      (verified ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600");
    makeBubble({ who: "you", text: `Verification ${verified ? "successful" : "failed"}.` });
  } catch {
    verified = false;
    verifyStatus.textContent = "❌ Not verified";
    verifyStatusBadge.textContent = "Not verified";
    verifyStatusBadge.className = "text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600";
    makeBubble({ who: "you", text: "Verification failed to submit." });
  }
});

// ===== Policies list =====
async function refreshPolicyList() {
  try {
    const items = await callBackend("/policies");
    policyList.innerHTML = items
      .map(i => {
        const d = new Date(i.updated_at).toLocaleString();
        return `
        <div class="py-3 flex items-start gap-3">
          <div class="mt-1 h-2 w-2 rounded-full bg-slate-300"></div>
          <div>
            <div class="font-medium text-slate-800">${escapeHtml(i.topic)}</div>
            <div class="text-xs text-slate-500">
              Section: ${escapeHtml(i.section)} ·
              <span class="uppercase">${escapeHtml(i.classification)}</span> ·
              ${d}
            </div>
          </div>
        </div>`;
      })
      .join("");
  } catch {
    policyList.textContent = "Failed to load policies.";
  }
}
refreshPolicies?.addEventListener("click", refreshPolicyList);
refreshPolicyList();

// ===== GPT Realtime API Integration =====
async function startCall() {
  console.log("Starting GPT Realtime connection...");
  setStatus("starting…", "bg-amber-400");
  clearTranscript();

  try {
    // Connect to our backend WebSocket proxy instead of directly to OpenAI
    console.log("Connecting to backend WebSocket proxy...");
    const wsUrl = `ws://localhost:8001/ws/realtime`;
    console.log("WebSocket URL:", wsUrl);
    
    websocket = new WebSocket(wsUrl);
    
    // Add connection timeout
    const connectionTimeout = setTimeout(() => {
      if (websocket.readyState === WebSocket.CONNECTING) {
        console.error("❌ WebSocket connection timeout");
        websocket.close();
        setStatus("connection timeout", "bg-rose-500");
        makeBubble({ who: "agent", text: "❌ Connection timeout. Please try again." });
      }
    }, 30000); // 30 second timeout

    websocket.onopen = async () => {
      clearTimeout(connectionTimeout);
      console.log("✅ WebSocket connected to backend proxy");
      setStatus("connected", "bg-emerald-500");
      makeBubble({ who: "agent", text: "🎉 Connected to GPT Realtime! I'm ready to help you." });
      
      // Initialize audio context for playback
      try {
        await initAudioContext();
        console.log("🔊 Audio context initialized");
      } catch (error) {
        console.warn("⚠️ Could not initialize audio context:", error);
      }
      
      // Initialize microphone for input
      try {
        const micInitialized = await initMicrophone();
        if (micInitialized) {
          console.log("🎤 Microphone ready");
          // Start continuous recording for real-time audio input
          startRecording();
          makeBubble({ who: "agent", text: "🎤 Ready for natural conversation! Server-side VAD will detect when you speak." });
        }
      } catch (error) {
        console.warn("⚠️ Could not initialize microphone:", error);
      }
      
      // Connection is ready, no need to send test message
      console.log("✅ Connection established and ready for voice interaction");
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📨 Received WebSocket message:", data);
        
        // Handle different message types
        if (data.type === "error") {
          console.error("❌ Backend error:", data.error);
          makeBubble({ who: "agent", text: `❌ Error: ${data.error.message}` });
          return;
        }
        
        handleRealtimeEvent(data);
      } catch (err) {
        console.error("❌ Failed to parse WebSocket message:", err, event.data);
      }
    };

    websocket.onerror = (error) => {
      console.error("❌ WebSocket error:", error);
      console.error("❌ WebSocket readyState:", websocket.readyState);
      console.error("❌ WebSocket URL:", wsUrl);
      setStatus("connection error", "bg-rose-500");
      makeBubble({ who: "agent", text: "❌ WebSocket connection error. Check console for details." });
    };

    websocket.onclose = (event) => {
      console.log("🔌 WebSocket closed:", event.code, event.reason);
      console.log("🔌 Close code:", event.code);
      console.log("🔌 Close reason:", event.reason);
      setStatus("disconnected", "bg-slate-300");
      makeBubble({ who: "agent", text: `🔌 Connection closed (Code: ${event.code}). Click Connect to reconnect.` });
      websocket = null;
    };

  } catch (error) {
    console.error("❌ Failed to start call:", error);
    setStatus("failed to start", "bg-rose-500");
    makeBubble({ who: "agent", text: `❌ Failed to start: ${error.message}` });
  }
}

function stopCall() {
  // Stop recording
  if (audioProcessor && isRecording) {
    stopRecording();
  }
  
  // Close WebSocket
  if (websocket) {
    websocket.close();
    websocket = null;
  }
  
  // Stop audio processor
  if (audioProcessor) {
    audioProcessor.disconnect();
    audioProcessor = null;
  }
  
  // Stop media stream
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  
  // Reset state
  isListening = false;
  isRecording = false;
  recordingChunks = [];
  
  setStatus("idle", "bg-slate-300");
  console.log("🛑 Call stopped and resources cleaned up");
}

function sendMessage(message) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message));
  } else {
    console.warn("WebSocket not ready, message not sent:", message);
  }
}

// ===== Handle Realtime events from GPT Realtime API =====
async function handleRealtimeEvent(evt) {
  console.log("📨 Received event:", evt.type, evt);

  // --- Assistant text stream ---
  if (evt.type === "response.text.delta" && typeof evt.delta === "string") {
    updateAgentPartial(evt.delta);
    return;
  }
  
  if (evt.type === "response.text.done" && typeof evt.text === "string") {
    finalizeAgentPartial(evt.text);
    return;
  }

  // --- Assistant audio stream ---
  if (evt.type === "response.audio.delta" && evt.delta) {
    console.log("🔊 Received audio delta, length:", evt.delta.length);
    // Handle audio data - play it through the audio element
    playAudioDelta(evt.delta);
    return;
  }
  
  // Debug: Log response data to see what we're getting
  if (evt.type === "response.done") {
    console.log("🔍 Response data:", evt.response);
    if (evt.response && evt.response.status === 'failed') {
      console.error("❌ RESPONSE FAILED!");
      console.error("❌ Error details:", evt.response.status_details);
      if (evt.response.status_details && evt.response.status_details.error) {
        console.error("❌ FULL ERROR:", JSON.stringify(evt.response.status_details.error, null, 2));
      }
    }
    if (evt.response && evt.response.output) {
      console.log("🔍 Response output:", evt.response.output);
      // Check if there's audio in the response
      if (evt.response.output.some && evt.response.output.some(item => item.type === 'audio')) {
        console.log("🔊 Found audio in response!");
      } else {
        console.log("❌ No audio found in response - only text");
      }
    }
  }
  
  if (evt.type === "response.audio.done") {
    console.log("✅ Audio response completed");
    return;
  }

  // --- Server-side VAD Events (Latest API) ---
  if (evt.type === "input_audio_buffer.speech_started") {
    console.log("🎤 User speech detected by server-side VAD");
    setStatus("listening", "bg-red-500");
    return;
  }

  if (evt.type === "input_audio_buffer.speech_stopped") {
    console.log("🔇 User speech ended - server-side VAD");
    setStatus("processing", "bg-amber-400");
    // Server-side VAD will automatically commit and create response
    return;
  }

  if (evt.type === "input_audio_buffer.committed") {
    console.log("📤 Audio buffer committed by server");
    return;
  }

  if (evt.type === "response.created") {
    console.log("🤖 AI response started");
    return;
  }

  if (evt.type === "response.done") {
    console.log("✅ Response completed");
    setStatus("connected", "bg-emerald-500");
    return;
  }

  // --- Assistant audio transcript stream ---
  if (evt.type === "response.audio_transcript.delta" && typeof evt.delta === "string") {
    updateAgentPartial(evt.delta);
    return;
  }
  
  if (evt.type === "response.audio_transcript.done" && typeof evt.transcript === "string") {
    finalizeAgentPartial(evt.transcript);
    return;
  }

  // --- User input speech transcription ---
  if (evt.type === "conversation.item.input_audio_transcription.delta" && typeof evt.delta === "string") {
    updateUserPartial(evt.delta);
    return;
  }
  
  if (evt.type === "conversation.item.input_audio_transcription.done" && typeof evt.transcript === "string") {
    finalizeUserPartial(evt.transcript);
    return;
  }

  // --- Tool calling (function calling) ---
  if (evt.type === "response.tool_calls" && evt.tool_calls) {
    for (const toolCall of evt.tool_calls) {
      await handleToolCall(toolCall);
    }
    return;
  }

  // --- Session events ---
  if (evt.type === "session.created") {
    makeBubble({ who: "agent", text: "Session ready. How can I help you today?" });
    return;
  }

  if (evt.type === "session.updated") {
    console.log("✅ Session updated");
    return;
  }
  
  if (evt.type === "error") {
    makeBubble({ who: "agent", text: `Error: ${evt.error?.message || "Unknown error"}` });
    return;
  }
}

// ===== Handle Tool Calls =====
async function handleToolCall(toolCall) {
  const { id, function: func, arguments: args } = toolCall;
  
  try {
    let result;
    
    if (func.name === "verify_customer") {
      const parsedArgs = JSON.parse(args);
      console.log("🔍 Verifying customer:", parsedArgs);
      
      const res = await callBackend("/verify", "POST", {
        email: parsedArgs.email || vEmail.value,
        full_name: parsedArgs.full_name || vName.value,
        last4: parsedArgs.last4 || vLast4.value,
        order_id: parsedArgs.order_id || vOrder.value
      });
      
      verified = !!res.verified;
      verifyStatusBadge.textContent = verified ? "Verified" : "Not verified";
      verifyStatusBadge.className =
        "text-xs px-2 py-1 rounded-full " +
        (verified ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600");
      
      result = { verified: res.verified };
      console.log("✅ Customer verification result:", result);
      
    } else if (func.name === "get_policy") {
      if (!verified) {
        result = { error: "verification_required", message: "Customer must be verified to access internal policies" };
        console.log("❌ Policy access denied - verification required");
      } else {
        const parsedArgs = JSON.parse(args);
        console.log("📋 Fetching policy:", parsedArgs);
        
        const res = await callBackend("/policy", "POST", {
          topic: (parsedArgs.topic || "").trim(),
          detail_level: parsedArgs.detail_level || "summary"
        });
        
        // Show policy in chat
        if (res?.text) {
          makeBubble({ who: "agent", text: res.text });
        }
        
        result = res;
        console.log("✅ Policy fetched successfully:", result);
      }
    } else {
      result = { error: `Unknown tool: ${func.name}` };
      console.log("❌ Unknown tool called:", func.name);
    }

    // Send tool call result back to GPT Realtime
    console.log("📤 Sending tool call result:", result);
    sendMessage({
      type: "response.tool_call_output",
      tool_call_id: id,
      output: result
    });

  } catch (err) {
    console.error("❌ Tool call error:", err);
    sendMessage({
      type: "response.tool_call_output",
      tool_call_id: id,
      output: { error: String(err) }
    });
  }
}

// ===== Wire buttons =====
connectBtn.addEventListener("click", startCall);
disconnectBtn.addEventListener("click", stopCall);

// Activate Audio button - required for Web Audio API
document.getElementById("activateAudioBtn").addEventListener("click", async () => {
  try {
    console.log("🔊 Activating audio context...");
    await initAudioContext();
    
    // Test audio with a simple beep
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.3);
    
    console.log("✅ Audio context activated and tested!");
    makeBubble({ who: "system", text: "🔊 Audio activated! You should hear a beep. Now you can start talking." });
    
    // Hide the button after activation
    document.getElementById("activateAudioBtn").style.display = "none";
    
  } catch (error) {
    console.error("❌ Audio activation failed:", error);
    makeBubble({ who: "system", text: "❌ Audio activation failed. Check browser console for details." });
  }
});

// Demo button functionality - use real P&C customer data
demoBtn.addEventListener("click", () => {
  vEmail.value = "maria92@example.com";
  vName.value = "Heather Gray";
  vLast4.value = "1234";
  vOrder.value = "POLICY-1632-Re";
  makeBubble({ who: "you", text: "📝 Demo P&C customer data loaded! Click 'Submit Verification' to test." });
});

// Add visual indicator for voice activity detection
document.addEventListener("DOMContentLoaded", () => {
  // Add instructions
  const instructions = document.createElement("div");
  instructions.className = "text-center text-slate-500 text-sm mt-4 p-3 bg-slate-50 rounded-lg";
  instructions.innerHTML = `
    <div class="font-medium mb-1">Natural Voice Conversation</div>
    <div>🗣️ Just speak naturally - Server-side VAD detects your speech automatically</div>
    <div class="text-xs mt-1">No buttons needed - powered by OpenAI's latest gpt-realtime model!</div>
  `;
  
  // Insert after the transcript
  const transcript = document.getElementById("transcript");
  transcript.parentNode.insertBefore(instructions, transcript.nextSibling);
});