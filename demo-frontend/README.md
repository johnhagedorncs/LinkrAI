# Healthcare Agent Demo Frontend

A simple React frontend that demonstrates the healthcare agent system by recording doctor-patient conversations, transcribing them, and routing tasks to specialized AI agents.

## Architecture

```
React Frontend (port 3000)
    ↓ HTTP
FastAPI Backend (port 8000)
    ├─→ Scribe Agent (AWS Transcribe Medical)
    └─→ Host Agent (port 8083)
            └─→ Referral Agent (port 10004)
            └─→ Scheduling Agent (port 10005)
            └─→ Other agents...
```

## Features

- 🎤 **Audio Recording** - Record doctor-patient conversations directly in browser
- 📝 **Medical Transcription** - AWS Transcribe Medical with speaker diarization
- 🤖 **Agent Orchestration** - Automatically routes tasks to specialized agents
- 📊 **Results Visualization** - Shows what actions the agents took

## Prerequisites

- Python 3.9+
- Node.js 18+
- AWS credentials (for S3 and Transcribe)
- Running agent infrastructure (host agent, referral agent, etc.)

## Setup

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

The `.env` file has been copied from the scribe agent. Verify it contains:

```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
TRANSCRIBE_OUTPUT_BUCKET=artera-transcriptions
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running the Demo

### Step 1: Start the Agent Infrastructure

Open separate terminal windows for each agent:

```bash
# Terminal 1: Host Agent
cd ../A2A-Framework/host_agent
uv run .
# Should see: "Running on local URL: http://0.0.0.0:8083"

# Terminal 2: Referral Agent
cd ../A2A-Framework/referral_agent
uv run .
# Should see: "Uvicorn running on http://0.0.0.0:10004"

# Terminal 3: Scheduling Agent (optional)
cd ../A2A-Framework/scheduling_agent
uv run .
# Should see: "Uvicorn running on http://0.0.0.0:10005"
```

### Step 2: Start the Backend API

```bash
# Terminal 4: Demo Backend
cd demo-frontend/backend
uvicorn main:app --reload --port 8000
# Should see: "Uvicorn running on http://127.0.0.1:8000"
```

### Step 3: Start the Frontend

```bash
# Terminal 5: Demo Frontend
cd demo-frontend/frontend
npm run dev
# Should see: "Local: http://localhost:3000"
```

### Step 4: Use the Demo

1. Open http://localhost:3000 in your browser
2. Click "🎤 Start Recording"
3. Allow microphone access
4. Have a simulated doctor-patient conversation
5. Click "⏹️ Stop Recording"
6. Watch as the system:
   - Uploads to S3
   - Transcribes with AWS Transcribe Medical
   - Processes through agent system
   - Shows results

## Example Conversation

Try this sample conversation for testing:

**Doctor (you):** "Hello, what brings you in today?"

**Patient (you):** "I've been having chest pain that started this morning."

**Doctor:** "Can you describe the pain? Is it sharp or dull?"

**Patient:** "It's a sharp pain in the center of my chest, especially when I breathe deeply."

**Doctor:** "Any shortness of breath or palpitations?"

**Patient:** "Yes, a little shortness of breath."

**Doctor:** "I think we should get you to see a cardiologist. I'll create a referral for you."

The system should automatically:
- Detect the need for a cardiology referral
- Create the referral order
- Optionally schedule an appointment

## Mock Mode (No AWS Required)

If you don't have AWS credentials or want to test quickly, the backend includes mock responses:

1. In `backend/main.py`, `SCRIBE_AVAILABLE` will be `False` if scribe agent isn't found
2. It will use a pre-written transcript instead of calling AWS Transcribe
3. The agent processing still works normally

## Troubleshooting

### "Failed to access microphone"
- Grant microphone permissions in your browser
- Try using Chrome or Firefox (Safari may have issues)

### "Transcription failed"
- Check AWS credentials in `backend/.env`
- Verify S3 bucket `artera-transcriptions` exists
- Check AWS Transcribe is available in your region

### "Processing failed"
- Ensure host agent is running on port 8083
- Check that referral agent is running on port 10004
- Look at backend logs for detailed errors

### Backend not connecting to scribe agent
- The backend imports from `../../Athena/scribe_agent/transcriber.py`
- If import fails, it falls back to mock mode
- Check that the path is correct relative to `demo-frontend/backend/`

## Development

### Backend Development

```bash
cd backend
# Run with auto-reload
uvicorn main:app --reload --port 8000

# Or run directly
python main.py
```

### Frontend Development

```bash
cd frontend
# Development mode with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
demo-frontend/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # AWS credentials
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main component
│   │   ├── App.css          # Styles
│   │   ├── api.ts           # API client
│   │   └── main.tsx         # Entry point
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
└── README.md                # This file
```

## Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- boto3 - AWS SDK for S3 upload
- Scribe Agent - Medical transcription (AWS Transcribe)

**Frontend:**
- React 18 - UI library
- TypeScript - Type safety
- Vite - Fast build tool
- Web Audio API - Browser audio recording

## Next Steps

**Enhancements you could add:**

1. **Real Agent Integration** - Call actual host agent API instead of mock processing
2. **WebSocket Streaming** - Show real-time agent activity
3. **Patient Context** - Add form to input patient name/ID
4. **Audio Playback** - Let users review recording before submitting
5. **Session History** - Store and display past conversations
6. **Better Error Handling** - More detailed error messages
7. **Loading States** - Better progress indicators
8. **Visualization** - Agent flow diagram showing routing

## License

Internal demo project for Artera Healthcare Agent System.
