# How to Run the A2A Multi-Agent System

## Quick Start Guide

### Terminal 1: Start Scheduling Agent (A2A Server)

```bash
cd /Users/adenj/CS/Artera/artera/A2A-Framework/scheduling_agent

# Start the scheduling agent on port 10005
uv run python __main__.py --port 10005
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10005 (Press CTRL+C to quit)
```

---

### Terminal 2: Start Host Agent (Gradio Web UI)

```bash
cd /Users/adenj/CS/Artera/artera/A2A-Framework/host_agent

# Start the host agent with Gradio UI
uv run .
```

**Expected Output:**
```
Running on local URL:  http://127.0.0.1:7860

To create a public link, set `share=True` in `launch()`.
```

---

## 🌐 Access the Web Interface

1. Open your browser
2. Go to: **http://127.0.0.1:7860**
3. You'll see a chat interface (Gradio)

---

## 💬 Example Interactions

### Test 1: Find Cardiology Appointments
```
Find cardiology appointments for patient 60183
```

**What happens:**
1. Host agent receives your message
2. Host agent calls Scheduling Agent via A2A
3. Scheduling agent searches all cardiology providers
4. Returns top 3 appointment options
5. You see the results in the web UI

### Test 2: Book an Appointment
```
Book option 2 from the previous results
```

**What happens:**
1. Host agent extracts appointment details
2. Calls Scheduling Agent to book
3. Returns confirmation

### Test 3: Try Different Specialties
```
Find family medicine appointments for patient 60183
```

---

## 🔍 Debugging Tips

### Check Scheduling Agent is Running
```bash
curl http://localhost:10003/.well-known/agent-card
```

Should return the agent card JSON.

### View Logs
- **Scheduling Agent:** See terminal 1 for Athena API calls
- **Host Agent:** See terminal 2 for A2A message routing

### Common Issues

**Issue:** "Connection refused to localhost:10003"
**Fix:** Make sure scheduling agent is running in Terminal 1

**Issue:** "No agents found"
**Fix:** Wait 5-10 seconds after starting scheduling agent for host to discover it

---

## 🛑 Stopping the Agents

- Press `CTRL+C` in each terminal to stop
- Or close the terminals

---

## 📊 What You Can Ask the Host Agent

✅ "Find [specialty] appointments for patient [id]"
✅ "Book appointment [id] for patient [id]"
✅ "Show available slots for cardiology"
✅ "Schedule a family medicine appointment"

The host agent will automatically route your request to the scheduling agent!
