# LinkrAI Demo Walkthrough

## What You'll See in the Live Demo

When you visit [https://linkrai-johnhagedorn.vercel.app](https://linkrai-johnhagedorn.vercel.app), here's the complete workflow:

---

## Step 1: Record Conversation

**What you see:**
- "Start Recording" button
- (Or click immediately to use mock data without recording)

**What happens behind the scenes:**
- If you record audio: Browser captures audio → uploads to backend → returns mock transcript
- Mock mode (no AWS): Skips S3 upload, returns pre-loaded oncology scenario
- Shows progress: "Uploading audio to S3..." → "Transcribing with AWS Transcribe Medical..."

---

## Step 2: Transcript

**What you see:**
A formatted doctor-patient conversation:

```
Doctor: Good morning. Come on in and have a seat. I've got your recent lab
results and biopsy back. How are you feeling today?

Patient: Um, I'm doing okay, I guess. A little nervous, to be honest. You
said you wanted to talk about some test results?

Doctor: Yes, I do. So a few weeks ago we checked your PSA level, and it
came back elevated at 12.4, which is higher than we'd like to see. We then
did a biopsy to get a better picture of what's going on, and I'm afraid the
results show prostate cancer.

Patient: Oh wow. Okay. Um... is this serious?

Doctor: I understand this is difficult news. The good news is we caught it,
and based on the biopsy findings, we're looking at what's called a Gleason 7
adenocarcinoma. That tells us about the grade and type of cancer cells...

[continues with full consultation]
```

**Key details in the conversation:**
- **Diagnosis:** Prostate cancer (Gleason 7 adenocarcinoma)
- **PSA Level:** 12.4 (elevated)
- **Action:** Doctor refers patient to oncology
- **Next Steps:** Oncology department will schedule appointment

---

## Step 3: Agent Actions

### Purple Box - Agents Called:
```
🏥 Referral Agent called
📅 Scheduling Agent called
💬 Messaging Agent called
```

### Results Section - Detailed Workflow:

#### 1. Host Agent → Referral Agent
```
Task: Create a medical referral for oncology consultation based on
prostate cancer diagnosis (Gleason 7 adenocarcinoma, PSA 12.4)
```

#### 2. 🏥 Referral Agent Tool: create_referral

**Input:**
```json
{
  "patient_id": "12345",
  "specialty": "oncology",
  "diagnosis_code": "C61",
  "diagnosis_description": "Malignant neoplasm of prostate (Gleason 7 adenocarcinoma)",
  "priority": "routine",
  "clinical_notes": "PSA 12.4, biopsy confirms prostate cancer. Patient needs
  oncology consultation for staging and treatment planning."
}
```

**Output:**
```
✅ Referral created successfully
Referral ID: REF-789456
Specialty: Oncology
Priority: Routine
Status: Pending oncology department review
```

**👆 THIS IS THE REFERRAL!** - You can see all the details:
- Referral ID for tracking
- Diagnosis code (C61 = prostate cancer)
- Clinical notes explaining why the referral is needed
- Priority level (routine)

---

#### 3. Referral Agent → Host Agent
```
Referral created successfully. Referral ID: REF-789456. Patient will be
contacted by oncology department within 5-7 business days.
```

---

#### 4. Host Agent → Scheduling Agent
```
Task: Find next available oncology appointments for patient 12345
```

#### 5. 📅 Scheduling Agent Tool: search_appointments

**Input:**
```json
{
  "patient_id": "12345",
  "specialty": "oncology",
  "department_id": "150",
  "days_ahead": 30
}
```

**Output:**
```
✅ Found 3 available appointments:

1. Provider: Dr. Sarah Chen (ID: 450)
   Date: January 25, 2026
   Time: 10:00 AM
   Location: Cancer Treatment Center

2. Provider: Dr. Michael Rodriguez (ID: 451)
   Date: January 26, 2026
   Time: 2:30 PM
   Location: Oncology Clinic - Building B

3. Provider: Dr. Emily Thompson (ID: 452)
   Date: January 27, 2026
   Time: 9:00 AM
   Location: Cancer Treatment Center
```

---

#### 6. Scheduling Agent → Host Agent
```
Found 3 available appointment slots:
1. Dr. Sarah Chen - Jan 25, 2026 at 10:00 AM
2. Dr. Michael Rodriguez - Jan 26, 2026 at 2:30 PM
3. Dr. Emily Thompson - Jan 27, 2026 at 9:00 AM
```

---

#### 7. Host Agent → Messaging Agent
```
Task: Send SMS to patient at 5555551234 with referral confirmation and
appointment options
```

#### 8. 💬 Messaging Agent Tool: send_sms

**Input:**
```json
{
  "phone_number": "5555551234",
  "message": "Your oncology referral has been created (REF-789456). Available
  appointments: Jan 25 at 10AM (Dr. Chen), Jan 26 at 2:30PM (Dr. Rodriguez),
  Jan 27 at 9AM (Dr. Thompson). Reply with preferred date or call 555-0100
  to schedule."
}
```

**Output:**
```
✅ SMS sent successfully
Recipient: +1-555-555-1234
Message ID: SM-abc123def456
Status: Delivered
Timestamp: 2026-01-19 14:30:22 UTC
```

---

#### 9. Messaging Agent → Host Agent
```
SMS sent successfully to 555-555-1234. Message: 'Your oncology referral has
been created. Available appointments: Jan 25 (Dr. Chen), Jan 26 (Dr. Rodriguez),
Jan 27 (Dr. Thompson). Reply with preferred date or call 555-0100 to schedule.'
```

---

## Summary

### What the Demo Shows:

1. **🎤 Audio Input** - Doctor-patient conversation about prostate cancer diagnosis
2. **📝 Medical Transcription** - Clean transcript extraction
3. **🤖 AI Understanding** - Host agent analyzes conversation and identifies need for:
   - Medical referral to oncology
   - Appointment scheduling
   - Patient notification
4. **🏥 Referral Creation** - Complete referral with diagnosis codes and clinical notes
5. **📅 Smart Scheduling** - Finds 3 available oncology appointments within 30 days
6. **💬 Patient Communication** - Sends SMS with referral ID and appointment options

### Key Technical Highlights:

- **Multi-Agent Orchestration**: Host agent intelligently routes tasks to specialized agents
- **EHR Integration**: Creates proper medical referrals with ICD-10 codes
- **Real-World Workflow**: Mimics actual healthcare provider operations
- **HIPAA Considerations**: Secure handling of patient information
- **Tool Use**: Each agent has specialized tools (create_referral, search_appointments, send_sms)

---

## Try It Yourself!

Visit: **[https://linkrai-johnhagedorn.vercel.app](https://linkrai-johnhagedorn.vercel.app)**

1. Click "Start Recording" (or just let it use mock data)
2. Watch the agents work in real-time
3. See the complete referral, appointments, and SMS notification

No credentials needed - runs in full mock mode for demo purposes!
