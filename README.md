# 🎙️ Voice Agent GPT Realtime

[![GitHub Repository](https://img.shields.io/badge/GitHub-VoiceAgent_GPTRealtime-blue?style=for-the-badge&logo=github)](https://github.com/vinoth12940/VoiceAgent_GPTRealtime)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](requirements.txt)
[![OpenAI](https://img.shields.io/badge/OpenAI-Realtime_API-orange?style=for-the-badge&logo=openai)](https://platform.openai.com/docs/guides/realtime-websocket)

A sophisticated real-time voice AI agent powered by OpenAI's latest GPT Realtime API, featuring advanced tool calling capabilities for P&C (Property & Casualty) insurance customer service.

## 📚 **Documentation Suite**

| Document | Description | Quick Access |
|----------|-------------|--------------|
| 📖 **[README.md](README.md)** | Complete technical documentation | *You are here* |
| 🚀 **[QUICK_START.md](QUICK_START.md)** | 5-minute setup guide | [Get started instantly →](QUICK_START.md) |
| 📊 **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** | Business case & ROI analysis | [View business impact →](EXECUTIVE_SUMMARY.md) |
| 🔄 **[WORKFLOW_ANALYSIS.md](WORKFLOW_ANALYSIS.md)** | Detailed workflow & cost analysis | [See cost savings →](WORKFLOW_ANALYSIS.md) |

**🎯 New to this project?** Start with the **[Quick Start Guide](QUICK_START.md)** for immediate setup, or review the **[Executive Summary](EXECUTIVE_SUMMARY.md)** for business impact.

## 🌟 Features

- **🎤 Real-time Voice AI**: Powered by OpenAI's `gpt-realtime` model with server-side Voice Activity Detection (VAD)
- **🔧 Advanced Tool Calling**: Intelligent function calling for customer verification and policy management
- **🌐 WebSocket Communication**: Seamless real-time bidirectional communication with OpenAI Realtime API
- **🔐 Customer Verification**: Secure multi-factor customer verification system
- **📋 P&C Policy Management**: Comprehensive Property & Casualty insurance policy database
- **🎯 Access Control**: Role-based access for internal and restricted policies
- **💻 Modern UI**: Clean, responsive interface built with Tailwind CSS
- **🔊 Direct Audio Processing**: Float32 → PCM16 conversion for optimal audio quality
- **📊 Real-time Transcription**: Live conversation transcripts with partial updates

## 🏗️ Architecture

```
Frontend (WebSocket) ←→ Backend (FastAPI) ←→ OpenAI Realtime API
                         ↓
                    SQLite Database
                  (Policies & Customers)
```

### Core Components

- **Frontend**: Real-time WebSocket client with direct audio processing
- **Backend**: FastAPI server with WebSocket proxy and business logic
- **Database**: SQLite with P&C insurance policies and customer data
- **OpenAI Integration**: Latest GPT Realtime API with server-side VAD

## 🛠️ Installation

### Prerequisites

- **Python 3.8+**
- **OpenAI API key** with GPT Realtime access
- **Modern web browser** with WebSocket and MediaRecorder support

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/vinoth12940/VoiceAgent_GPTRealtime.git
   cd VoiceAgent_GPTRealtime
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

5. **Start the server**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
   ```

6. **Open your browser**
   Navigate to `http://localhost:8001`

## 🚀 Usage

### Quick Start

1. **Connect**: Click "Connect" to establish WebSocket connection
2. **Demo Data**: Click "Demo" to load sample customer information
3. **Start Conversation**: Begin speaking naturally - the AI will respond automatically
4. **Verification**: Provide customer details when prompted for policy access

### Voice Interaction Flow

1. **Greeting**: AI introduces itself as P&C insurance specialist
2. **Verification**: Requests email, name, and last 4 digits for identity verification
3. **Policy Lookup**: Retrieves and explains specific policy details
4. **Natural Conversation**: Responds to questions about coverage, premiums, and terms

## 🔧 API Endpoints

### Core Endpoints
- `GET /` - Main application interface
- `WebSocket /ws/realtime` - Real-time voice communication proxy

### Authentication & Verification
- `POST /api/verify` - Verify customer credentials
- `POST /api/realtime/session` - Create ephemeral OpenAI session

### Policy Management
- `GET /api/policies` - List all policies
- `GET /api/customer/{email}/policies` - Get customer-specific policies
- `GET /api/policy-details/{policy_number}` - Detailed policy information
- `POST /api/policy-status/{policy_number}` - Update policy status

### P&C Coverage Information
- `GET /api/pc-policies/auto` - Auto insurance policies
- `GET /api/pc-policies/property` - Property insurance policies  
- `GET /api/pc-coverage/{coverage_type}` - Coverage details by type

## 🎯 Tool Calling System

The system integrates seamlessly with OpenAI's tool calling capabilities:

### Available Tools

1. **verify_customer**
   - **Purpose**: Verify customer identity before sharing sensitive information
   - **Parameters**: `email`, `full_name`, `last4`, `order_id`
   - **Returns**: Boolean verification status

2. **get_customer_policies**
   - **Purpose**: Retrieve all P&C policies for verified customers
   - **Parameters**: `email`
   - **Returns**: Array of policy details with premiums, coverage, due dates

3. **get_pc_coverage_info**
   - **Purpose**: Get general P&C coverage information
   - **Parameters**: `coverage_type` (auto, homeowners, commercial, liability, claims)
   - **Returns**: Detailed coverage information and terms

### Tool Call Architecture

```
User Voice Input → OpenAI Realtime → Function Call Detection → Backend Tool Execution → Database Query → Response to OpenAI → Voice Output
```

## 🔒 Security Features

- **Session-based Verification**: Customer verification tied to WebSocket sessions
- **Multi-factor Authentication**: Email, name, and last4 verification required
- **Access Control**: Internal/restricted policies require customer verification
- **Secure API Proxy**: Server-side OpenAI API key management
- **Data Protection**: Customer data validation and sanitization

## 📊 Database Schema

### Customers Table
```sql
customers (
  id INTEGER PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  last4 TEXT,           -- Last 4 digits (phone/card)
  order_id TEXT         -- Recent order/policy ID
)
```

### Customer Policies Table
```sql
customer_policies (
  id INTEGER PRIMARY KEY,
  customer_email TEXT,
  policy_number TEXT,
  first_name TEXT,
  last_name TEXT,
  premium REAL,
  coverage_type TEXT,
  next_due_date TEXT,
  payment_method TEXT,
  status TEXT,
  created_at TIMESTAMP
)
```

### P&C Policies Table
```sql
policies (
  id INTEGER PRIMARY KEY,
  topic TEXT UNIQUE,
  content TEXT,
  classification TEXT,   -- public, internal, restricted
  created_at TIMESTAMP
)
```

## 🎨 Frontend Features

### Audio Processing
- **Direct Float32 Processing**: ScriptProcessor for real-time audio capture
- **PCM16 Conversion**: Optimized audio format for OpenAI Realtime API
- **Server-side VAD**: Automatic speech detection without client-side processing
- **Web Audio API**: Professional audio playback with queue management

### UI Components
- **Real-time Transcription**: Live conversation display with partial updates
- **Connection Status**: Visual indicators for WebSocket and AI connection states
- **Demo Data**: One-click loading of sample customer information
- **Policy Display**: Formatted display of customer policies and coverage details

## 🧪 Testing

### Demo Customer Data

**Primary Test Customer:**
- Email: `maria92@example.com`
- Name: `Heather Gray`
- Last4: `1234`
- Policy: `POLICY-1632-Re`

**Additional Test Customers:**
- `benjamin77@example.org` - Judy Griffin (Last4: `5419`)
- `martinheather@example.org` - Patrick Jimenez (Last4: `7625`)
- `qcervantes@example.com` - Jason Harrington (Last4: `9810`)
- `andrewstaylor@example.com` - Mr. Jordan Graves Jr. (Last4: `3228`)

### Testing Scenarios

1. **Voice Verification**: "I need help with my policy information"
2. **Policy Inquiry**: "What's my current premium and coverage?"
3. **Coverage Questions**: "Can you explain my auto insurance deductible?"
4. **General Information**: "What types of coverage do you offer?"

## 📁 Project Structure

```
VoiceAgentGPTRealtime/
├── backend/
│   ├── main.py          # FastAPI app with WebSocket proxy
│   ├── routes.py        # API endpoints for policies and verification
│   ├── auth.py          # OpenAI integration and session management
│   ├── db.py            # Database operations and seeding
│   ├── models.py        # Pydantic data models
│   └── config.py        # Configuration and environment variables
├── frontend/
│   ├── index.html       # Main UI with Tailwind CSS
│   └── app.js           # WebSocket client and audio processing
├── policies.db          # SQLite database with P&C data
├── requirements.txt     # Python dependencies
├── README.md           # This documentation
└── QUICK_START.md      # Quick setup guide
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `APP_ORIGIN` | Frontend origin for CORS | `http://127.0.0.1:8000` |
| `DB_PATH` | SQLite database path | `policies.db` |
| `ADMIN_SECRET` | Admin operations secret | `change-me` |
| `REALTIME_MODEL` | OpenAI Realtime model | `gpt-realtime` |
| `REALTIME_VOICE` | Voice selection | `alloy` |

### OpenAI Realtime Settings

- **Model**: `gpt-realtime` (Latest speech-to-speech model)
- **Voice**: `alloy` (Clear, professional voice)
- **Audio Format**: PCM16 at 24kHz for optimal quality
- **Turn Detection**: Server-side VAD for natural conversation flow
- **Modalities**: Both text and audio for comprehensive interaction

## 🚨 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   ```
   ❌ Check: OpenAI API key validity
   ❌ Check: GPT Realtime API access
   ❌ Check: Network connectivity
   ```

2. **Audio Input Not Working**
   ```
   ❌ Check: Browser microphone permissions
   ❌ Check: HTTPS requirement for MediaRecorder
   ❌ Check: Browser console for audio errors
   ```

3. **Tool Calls Not Executing**
   ```
   ❌ Check: Customer verification completion
   ❌ Check: Backend API endpoint availability
   ❌ Check: Database connectivity
   ```

4. **Voice Quality Issues**
   ```
   ❌ Check: Audio format configuration (PCM16)
   ❌ Check: Sample rate settings (24kHz)
   ❌ Check: Network bandwidth
   ```

### Debug Mode

Enable detailed logging:
1. **Browser Console**: F12 → Console tab
2. **Backend Logs**: Check terminal output for WebSocket events
3. **Network Tab**: Monitor WebSocket message flow

## 🔮 Future Enhancements

- [ ] **Multi-language Support**: Spanish, French customer service
- [ ] **Advanced Analytics**: Call duration, resolution metrics
- [ ] **CRM Integration**: Salesforce, HubSpot connectivity
- [ ] **Voice Customization**: Multiple voice options and speeds
- [ ] **Real-time Sentiment Analysis**: Customer satisfaction monitoring
- [ ] **Advanced Search**: Semantic policy search capabilities
- [ ] **Mobile App**: React Native or Flutter implementation
- [ ] **Call Recording**: Compliance and training features

## 📚 Resources & Documentation

### **Project Documentation**
- **[📖 README.md](README.md)** - Complete technical documentation *(You are here)*
- **[🚀 QUICK_START.md](QUICK_START.md)** - Get up and running in 5 minutes
- **[📊 EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - Business case, ROI analysis (335% ROI)
- **[🔄 WORKFLOW_ANALYSIS.md](WORKFLOW_ANALYSIS.md)** - Detailed cost-benefit analysis ($431K savings)
- **[📄 LICENSE](LICENSE)** - MIT License for open source use

### **GitHub Repository**
- **[🔗 Main Repository](https://github.com/vinoth12940/VoiceAgent_GPTRealtime)** - Complete source code
- **[📋 Issues](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/issues)** - Bug reports and feature requests
- **[🔀 Pull Requests](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/pulls)** - Code contributions
- **[📈 Insights](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/pulse)** - Repository analytics

### **External References**
- **[OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime-websocket)** - Official API documentation
- **[Realtime Prompting Guide](https://cookbook.openai.com/examples/realtime_prompting_guide)** - Best practices for prompting
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Backend framework docs
- **[WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)** - Frontend WebSocket reference
- **[Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)** - Audio processing reference

## 🤝 Contributing

We welcome contributions to the Voice Agent GPT Realtime project! Here's how to get started:

1. **Fork** the [repository](https://github.com/vinoth12940/VoiceAgent_GPTRealtime)
2. **Clone** your fork (`git clone https://github.com/YOUR_USERNAME/VoiceAgent_GPTRealtime.git`)
3. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
4. **Commit** your changes (`git commit -m 'Add amazing feature'`)
5. **Push** to the branch (`git push origin feature/amazing-feature`)
6. **Open** a [Pull Request](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/pulls)

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add type hints for all function parameters
- Include docstrings for public functions
- Test voice interactions with multiple browsers
- Ensure mobile responsiveness for UI changes

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues, questions, and feature requests:

1. **Check** the troubleshooting section above
2. **Review** browser console and backend logs  
3. **Test** with demo customer data
4. **Open** an [issue](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/issues) with detailed error information and steps to reproduce

### **Quick Links**
- 🐛 **[Report Bug](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/issues/new)** - Found an issue? Let us know!
- 💡 **[Request Feature](https://github.com/vinoth12940/VoiceAgent_GPTRealtime/issues/new)** - Have an idea? Share it!
- 📖 **[Documentation](https://github.com/vinoth12940/VoiceAgent_GPTRealtime#readme)** - Complete project docs
- 🚀 **[Quick Start](QUICK_START.md)** - Get started in 5 minutes

---

**🎉 Built with ❤️ using OpenAI's GPT Realtime API**

*Experience the future of voice-powered customer service with natural, intelligent conversations.*

**⭐ Star this repository** on [GitHub](https://github.com/vinoth12940/VoiceAgent_GPTRealtime) if you found it helpful!