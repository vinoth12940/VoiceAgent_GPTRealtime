# 🚀 Quick Start - Voice Agent GPT Realtime

Get your P&C insurance voice agent running in **5 minutes** with **WebRTC mode** for ultra-low latency!

## ⚡ **Instant Setup**

### **1. Environment Setup**
```bash
# Clone and navigate
cd VoiceAgentGPTRealtime

# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"
```

### **2. Start the Server**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

### **3. Open the Application**
- **Browser**: `http://localhost:8001` (auto-redirects to WebRTC mode ⚡)
- **Direct WebRTC**: `http://localhost:8001/index-webrtc.html`
- **You'll see**: Professional P&C insurance voice agent with modern chat interface

---

## 🎯 **5-Minute Test Flow (WebRTC Mode - Default)**

### **Step 1: Connect to AI**
1. **Click "Connect via WebRTC"** - Watch status turn green ✅
2. **See**: "🎉 Connected! Configuring AI agent..." message
3. **Grant**: Microphone permissions when prompted
4. **Auto-configured**: Ultra-low latency WebRTC connection established

### **Step 2: Load Demo Data**
1. **Click "Demo Data"** - Loads realistic customer info
2. **See**: Demo P&C customer data populated
3. **Data**: Heather Gray, maria92@example.com, Last4: 1234
4. **Note**: System accepts both "Gray" and "Grey" spelling

### **Step 3: Test Voice Interaction**
1. **Start Speaking**: "Hi, I need help with my insurance policy"
2. **AI Responds**: You'll see:
   - 🤖 **AI message on LEFT** with blue gradient bubble
   - 👤 **Your message on RIGHT** with green gradient bubble
   - **Typing indicator** (●●●) as AI speaks
3. **Watch Magic**: Form fields auto-populate as you speak
4. **Follow Prompts**: AI will verify email (spelled character-by-character), full name, and last 4 digits
5. **Experience**: Natural, low-latency voice conversation with policy details

---

## 🎤 **Voice Interaction Examples**

### **Try These Conversations:**

**🔍 Customer Verification:**
- "I need help with my policy information"
- *AI will ask for email, name, and last 4 digits*
- Use demo data: maria92@example.com, Heather Gray, 1234

**📋 Policy Inquiries:**
- "What's my current premium?"
- "When is my next payment due?"
- "Can you explain my coverage details?"

**💡 General Questions:**
- "What types of auto insurance do you offer?"
- "How does homeowners insurance work?"
- "What's the difference between comprehensive and collision?"

---

## ✅ **Success Indicators**

### **🟢 Everything Working (WebRTC Mode):**
- Status shows "Connected via WebRTC ⚡" with green dot
- AI introduces itself as "Alex", P&C insurance specialist
- Beautiful chat interface with avatars appears:
  - 🤖 Robot avatar for AI on the LEFT
  - 👤 Person avatar for you on the RIGHT
- Microphone captures your voice (see browser permission)
- Form fields flash yellow/blue as they auto-populate
- AI responds with ultra-low latency (50-100ms)
- Typing indicators (●●●) show when AI is speaking
- Customer verification works with demo data
- Policy information is retrieved and explained with ✅ system notifications

### **📊 Browser Console (F12):**
```
🎤 Raw audio chunk sent to OpenAI, samples: 4096
📥 OpenAI -> Frontend: response.audio.delta
✅ Customer verification result: true
🔧 Found function call in response.done: verify_customer
```

---

## 🚨 **Troubleshooting**

### **Connection Issues**
```bash
❌ "Failed to start" or "Connection error"
✅ Check: OpenAI API key in terminal environment
✅ Check: Server running on port 8001
✅ Check: Browser console (F12) for detailed errors
```

### **Audio Issues**
```bash
❌ "Not listening to voice" or no response
✅ Check: Microphone permissions granted
✅ Check: HTTPS (required for microphone access)
✅ Check: Browser compatibility (Chrome, Firefox, Safari)
```

### **Verification Issues**
```bash
❌ "Verification failed" or 403 errors
✅ Use: Demo button to load correct data
✅ Check: Database contains customer data
✅ Try: Exact demo values (maria92@example.com, Heather Gray, 1234)
```

---

## 🧪 **Advanced Testing**

### **Multiple Customers**
The database includes 5 test customers:

| Name | Email | Last4 | Policy Type |
|------|-------|-------|-------------|
| Heather Gray | maria92@example.com | 1234 | Auto |
| Judy Griffin | benjamin77@example.org | 5419 | Home |
| Patrick Jimenez | martinheather@example.org | 7625 | Auto |
| Jason Harrington | qcervantes@example.com | 9810 | Home |
| Jordan Graves Jr. | andrewstaylor@example.com | 3228 | Auto |

### **Test Scenarios**
1. **Happy Path**: Demo data → Verification → Policy lookup
2. **Error Handling**: Wrong last4 digits → Verification failure
3. **Coverage Questions**: Ask about deductibles, limits, exclusions
4. **Natural Flow**: Interrupt, ask follow-ups, request clarifications

---

## 🔧 **Development Mode**

### **Real-time Debugging**
```bash
# Terminal 1: Server with detailed logs
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001

# Terminal 2: Monitor database
sqlite3 policies.db "SELECT * FROM customers;"

# Browser: Console (F12) for frontend logs
```

### **Key Log Messages**
- `✅ Connected to OpenAI Realtime API` - Backend connected
- `🎤 Audio streaming started` - Frontend microphone active
- `🔧 Found function call` - Tool execution
- `📥 OpenAI -> Frontend: response.audio.delta` - AI speaking

---

## 📚 **Next Steps**

### **Customize for Your Use Case:**
1. **Update Customer Data**: Modify `backend/db.py` seeding functions
2. **Add New Policies**: Extend P&C coverage in database
3. **Customize Voice**: Change voice in `backend/config.py`
4. **Modify Prompts**: Update instructions in `backend/main.py`

### **Production Deployment:**
1. **Environment Variables**: Set production OpenAI API key
2. **Database**: Consider PostgreSQL for production
3. **HTTPS**: Required for microphone access
4. **Monitoring**: Add logging and error tracking

---

## 🎉 **You're Ready!**

Your P&C insurance voice agent is now running with:
- ✅ **Real-time voice interaction**
- ✅ **Customer verification system**  
- ✅ **Policy database integration**
- ✅ **Professional AI responses**
- ✅ **Natural conversation flow**

**🎤 Start talking to your AI insurance specialist!**

---

**📖 Need more details?** Check the full [README.md](README.md) for comprehensive documentation.

**🐛 Found an issue?** Open an issue with your browser console logs and steps to reproduce.