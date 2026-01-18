# LinkrAI - Healthcare Agent Orchestration Platform

> An AI-powered healthcare automation system that intelligently coordinates multiple specialized agents to handle medical referrals, appointment scheduling, and patient communication.

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://your-demo-url.vercel.app)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20S3-FF9900?logo=amazon-aws)](https://aws.amazon.com/)

⚠️ **DISCLAIMER:** This repository is a **demo** for educational and portfolio purposes only.
It is **not** intended for production use and does not contain any proprietary code or real healthcare data.

---

## 🎯 Project Overview

LinkrAI is a multi-agent AI system designed for healthcare automation. It demonstrates advanced agent orchestration, EHR integration, and intelligent task routing using modern AI technologies.

### Key Features

- **🎤 Medical Transcription** - Real-time audio capture with AWS Transcribe Medical
- **🤖 Multi-Agent Orchestration** - Intelligent routing via host agent using Claude Haiku 4.5
- **🏥 EHR Integration** - Direct integration with Athena Health API
- **📅 Smart Scheduling** - Automated appointment discovery and booking
- **💬 Patient Communication** - SMS notifications via Twilio/AWS SNS
- **🔒 HIPAA Considerations** - Secure handling of protected health information

---

## 🏗️ Architecture

```
┌─────────────┐
│   Patient   │
│  Recording  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│         React Frontend (Vite)               │
│  • Audio Recording (Web Audio API)          │
│  • Real-time Transcript Display             │
│  • Agent Action Visualization               │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│      FastAPI Backend (Port 8000)            │
│  • AWS S3 Upload                            │
│  • AWS Transcribe Medical                   │
│  • Agent API Gateway                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   Host Agent (Port 8084)                    │
│   Google ADK + AWS Bedrock Claude Haiku 4.5 │
│   • Intent Recognition                      │
│   • Workflow Orchestration                  │
│   • Agent-to-Agent Communication (A2A)      │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┬───────────────┐
       ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Referral │    │Scheduling│    │Messaging │
│  Agent   │    │  Agent   │    │  Agent   │
│          │    │          │    │          │
│ Port     │    │ Port     │    │ Port     │
│ 10004    │    │ 10005    │    │ 10003    │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     ▼               ▼               ▼
┌─────────────────────────────────────────────┐
│         External Services                   │
│  • Athena Health EHR API                    │
│  • AWS SNS (SMS)                            │
│  • Twilio (SMS Alternative)                 │
└─────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Purpose | Tools/APIs |
|-------|---------|------------|
| **Host Agent** | Orchestrates workflow, routes tasks to specialized agents | Google ADK, AWS Bedrock Claude |
| **Referral Agent** | Creates medical referrals with diagnosis codes | Athena Health API, SNOMED CT |
| **Scheduling Agent** | Finds and books appointments by specialty | Athena Health API |
| **Messaging Agent** | Sends SMS notifications to patients | AWS SNS, Twilio |

---

## 🚀 Live Demo

**[Try the Live Demo →](https://your-demo-url.vercel.app)**

The live demo runs in **mock mode** (no AWS credentials required) with pre-loaded medical scenarios.

### Demo Workflow

1. **Record** a doctor-patient conversation (or use simulated audio)
2. **Transcribe** the conversation using AWS Transcribe Medical
3. **Process** the transcript through the agent system
4. **View** real-time agent actions:
   - 🏥 Referral creation
   - 📅 Appointment scheduling
   - 💬 Patient SMS notification

---

## 🛠️ Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for blazing-fast builds
- **Web Audio API** for browser audio recording
- **Custom CSS** with dark mode theme

### Backend
- **FastAPI** (Python 3.11+)
- **AWS S3** for audio storage
- **AWS Transcribe Medical** for medical transcription
- **Athena Health API** for EHR integration

### AI & Agents
- **AWS Bedrock** (Claude Haiku 4.5) for agent intelligence
- **Google Agent Development Kit** for host agent orchestration
- **Model Context Protocol (MCP)** for tool/API integration

### Infrastructure
- **Vercel** (frontend hosting)
- **Render** (backend API hosting)
- **GitHub Actions** (CI/CD)

---

## 📦 Local Development Setup

### Prerequisites

```bash
# Required
- Python 3.11+
- Node.js 18+
- npm or yarn

# Optional (for full AWS integration)
- AWS Account (S3 + Transcribe + Bedrock)
- Athena Health API Credentials
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/LinkrAI.git
cd LinkrAI
```

2. **Set up environment variables**
```bash
cp example.env .env
# Edit .env with your credentials (or leave blank for mock mode)
```

3. **Start the backend**
```bash
cd demo-frontend/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

4. **Start the frontend** (in a new terminal)
```bash
cd demo-frontend/frontend
npm install
npm run dev
```

5. **Open your browser**
```
http://localhost:3000
```

### Mock Mode (No Credentials Required)

The system automatically detects missing AWS credentials and runs in **mock mode**:
- ✅ Pre-loaded medical transcript
- ✅ Simulated agent responses
- ✅ Full UI workflow demonstration
- ⚠️ No real AWS/EHR API calls

Perfect for local testing and demos!

---

## 🎬 Demo Scenarios

### Scenario 1: Cardiology Referral
```
Doctor: "I'm concerned about your chest pain. Let's get you to see a cardiologist."
Patient: "How soon can I get an appointment?"

→ Referral Agent creates cardiology referral
→ Scheduling Agent finds next 3 available slots
→ Messaging Agent sends SMS with appointment options
```

### Scenario 2: Oncology Consultation
```
Doctor: "Your biopsy results show prostate cancer. I'm referring you to oncology."
Patient: "What happens next?"

→ Referral Agent creates oncology referral with diagnosis codes
→ Scheduling Agent searches for oncology specialists
→ Messaging Agent sends confirmation and appointment details
```

---

## 📊 System Diagram

For a detailed Mermaid diagram of the complete system architecture, see [system_diagram.md](system_diagram.md).

---

## 🔐 Security & Privacy

### Data Handling
- ✅ **No PHI committed to git** - All sensitive data removed
- ✅ **Environment variables** for all credentials
- ✅ **Comprehensive .gitignore** for sensitive files
- ✅ **Mock mode** for public demos (no real patient data)

### Production Considerations
- HIPAA compliance required for real medical use
- End-to-end encryption for patient communications
- Audit logging for all agent actions
- Role-based access control (RBAC)

*Note: This is a demonstration project. Production deployment requires additional security hardening.*

---

## 📁 Project Structure

```
LinkrAI/
├── demo-frontend/
│   ├── frontend/          # React + TypeScript UI
│   │   ├── src/
│   │   │   ├── App.tsx    # Main application component
│   │   │   ├── api.ts     # Backend API client
│   │   │   └── App.css    # Styling
│   │   ├── vercel.json    # Vercel deployment config
│   │   └── package.json
│   └── backend/           # FastAPI server
│       ├── main.py        # API endpoints
│       ├── render.yaml    # Render deployment config
│       └── requirements.txt
├── A2A-Framework/         # Agent-to-Agent framework
│   ├── host_agent/        # Orchestration agent
│   ├── referral_agent/    # Medical referral creation
│   ├── scheduling_agent/  # Appointment management
│   └── messaging_agent/   # Patient communication
├── agents/                # Specialized agent implementations
├── Athena/                # Athena Health API utilities
├── example.env            # Environment template
├── system_diagram.md      # Architecture documentation
└── README.md             # This file
```

---

## 🚢 Deployment Guide

### Frontend (Vercel)

1. **Connect GitHub repo to Vercel**
2. **Set root directory**: `demo-frontend/frontend`
3. **Set environment variable**: `VITE_API_URL` → your Render backend URL
4. **Deploy!**

### Backend (Render)

1. **Create new Web Service**
2. **Connect GitHub repo**
3. **Set root directory**: `demo-frontend/backend`
4. **Use `render.yaml`** for automatic configuration
5. **Set environment variable** (optional): `FRONTEND_URL` → your Vercel URL
6. **Deploy!**

---

## 🧪 Testing

```bash
# Backend tests
cd A2A-Framework/scheduling_agent
python tests/test_sms_simulator.py

# Frontend (local)
cd demo-frontend/frontend
npm run dev
```

---

## 📈 Roadmap

- [ ] **Real-time WebSocket** for live agent updates
- [ ] **Multi-tenancy** support for multiple healthcare organizations
- [ ] **Analytics dashboard** for agent performance metrics
- [ ] **Additional agents**: Lab orders, prescription management, insurance verification
- [ ] **Voice synthesis** for patient-facing voice responses
- [ ] **Docker Compose** for one-command local setup

---

## 🤝 Contributing

This is a portfolio/demonstration project. While it's not actively maintained for production use, suggestions and feedback are welcome!

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 👨‍💻 About the Developer

Built by John Hagedorn as a demonstration of:
- Multi-agent AI orchestration
- Healthcare technology integration
- Full-stack development (React + FastAPI)
- Cloud architecture (AWS + Vercel + Render)
- EHR API integration (Athena Health)

**Contact**: [your.email@example.com](mailto:your.email@example.com)
**LinkedIn**: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
**Portfolio**: [yourportfolio.com](https://yourportfolio.com)

---

## 🙏 Acknowledgments

- **Athena Health** for sandbox API access
- **Anthropic** for Claude AI models via AWS Bedrock
- **AWS** for Transcribe Medical and infrastructure
- **Google** for Agent Development Kit

---

**⭐ If you found this project interesting, please star the repo!**
