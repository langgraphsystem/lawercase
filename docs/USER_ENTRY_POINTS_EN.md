# User Entry Points - MegaAgent EB-1A System

## Overview

MegaAgent EB-1A is an AI-powered immigration assistance system specializing in EB-1A visa petitions. This document describes all available user entry points and initial interactions with the platform.

**Production URLs:**
- **Frontend:** https://eb1a-frontend.vercel.app/
- **Backend API:** https://refreshing-reprieve-production-9802.up.railway.app

---

## 🚀 Three Ways to Get Started

### Option 1: Telegram Bot ⭐ RECOMMENDED for Clients

**Setup time: 2 minutes**

1. Find the bot in Telegram
2. Send `/start` command
3. Begin intake questionnaire with `/intake_start`
4. Answer questions step-by-step
5. Get analysis with `/eb1_analyze`

**Key Commands:**
- `/start` - Welcome and authorization
- `/intake_start` - Begin intake questionnaire (8 blocks)
- `/help` - List all available commands
- `/eb1_analyze` - Full EB-1A criteria analysis
- `/case_create` - Create a new case
- `/status` - Check system status

**Authorization:**
Access controlled via `TELEGRAM_ALLOWED_USERS` environment variable (comma-separated Telegram user IDs).

---

### Option 2: Web Interface (Next.js Frontend)

**Setup time: 5 minutes**

1. Navigate to https://eb1a-frontend.vercel.app/
2. Login with credentials
3. Create or select a case
4. Interact via chat interface
5. Monitor progress through dashboard

**Demo Accounts:**

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| Admin | admin@eb1a.com | demo1234 | Full access + metrics |
| Lawyer | lawyer@eb1a.com | demo1234 | Case management + tools |
| Client | client@eb1a.com | demo1234 | View own cases |

**Key Features:**
- Real-time chat with AI agent (SSE streaming)
- Case management dashboard
- Document upload and generation
- Multi-case support with localStorage history

---

### Option 3: Direct API Integration

**Setup time: 10 minutes**

**Step 1: Authenticate**
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "lawyer@eb1a.com",
  "password": "demo1234"
}

# Response:
# {
#   "access_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 86400,
#   "user_id": "lawyer-001",
#   "roles": ["lawyer"]
# }
```

**Step 2: Core Endpoints**

```bash
# Health Check
GET /health
GET /ready

# Ask Agent
POST /v1/ask
Authorization: Bearer <token>
{
  "query": "Analyze my EB-1A chances"
}

# Search Memory
POST /v1/search
Authorization: Bearer <token>
{
  "query": "patent applications",
  "top_k": 5
}

# Case Management
POST /api/v1/cases     # Create
GET  /api/v1/cases/{id} # Read
PUT  /api/v1/cases/{id} # Update
DELETE /api/v1/cases/{id} # Delete
```

**Step 3: Streaming via AG-UI Protocol**
```bash
POST /agui/run
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "Analyze EB-1A criteria",
  "case_id": "case-123",
  "stream": true
}

# Response via Server-Sent Events (SSE):
# event: RUN_START
# event: TEXT_CHUNK
# event: STEP_START / STEP_END
# event: RUN_COMPLETE
```

---

## 📋 Initial User Journey

### Path A: New Client (Telegram) ⭐ RECOMMENDED

```
1. /start
   └─> Welcome message + authorization check

2. /intake_start
   └─> Begin 8-block questionnaire:
       - Block 1: Basic Information (name, DOB, citizenship)
       - Block 2: Education (degrees, institutions)
       - Block 3: Career (positions, companies)
       - Block 4: Achievements (awards, publications, patents)
       - Block 5: Membership (professional organizations)
       - Block 6: Critical Role (judging, peer review)
       - Block 7: Media (press mentions)
       - Block 8: Commercial Success (income, sales)

3. Navigation:
   - ⏭ Skip question
   - ⏸ Pause and save progress
   - 🔙 Go back
   - ▶ Continue to next block

4. /eb1_analyze
   └─> Receive analysis of 10 EB-1A criteria
   └─> Get percentage score and recommendations

5. Next steps:
   - /generate_letter - Generate recommendation letters
   - /case_create - Create formal case
   - Upload documents via Telegram
```

### Path B: Lawyer/Professional (Web UI)

```
1. Login at https://eb1a-frontend.vercel.app/
   └─> JWT token stored in session (24h expiry)

2. Navigate to /chat
   └─> View list of cases
   └─> Select or create case

3. Interact via chat:
   └─> "What are the EB-1A criteria?"
   └─> "Analyze this case's chances"
   └─> "What documents are needed?"

4. Manage cases:
   └─> Dashboard view
   └─> Upload documents
   └─> Generate petition drafts
   └─> Export final package

5. Collaborate:
   └─> Share cases with team
   └─> Track progress
   └─> Monitor deadlines
```

### Path C: Developer/Integration (API)

```
1. Obtain JWT token via /auth/login

2. Create case via POST /api/v1/cases

3. Submit intake data programmatically

4. Trigger analysis via /v1/ask or workflow API

5. Retrieve results and documents

6. Integrate with existing systems
```

---

## 🎯 The 10 EB-1A Criteria

The system analyzes your profile against these criteria:

1. ✅ **Awards** - National or international prizes/awards
2. ✅ **Membership** - Associations requiring outstanding achievement
3. ✅ **Published Material** - About you in professional/major media
4. ✅ **Judging** - Judged the work of others in your field
5. ✅ **Original Contributions** - Scientific/scholarly/business/artistic
6. ✅ **Scholarly Articles** - Authored articles in professional publications
7. ✅ **Exhibitions** - Work displayed/showcased publicly
8. ✅ **Leading Role** - Critical/leading role in distinguished organizations
9. ✅ **High Salary** - Significantly higher than peers
10. ✅ **Commercial Success** - In performing arts/entertainment

**Requirement:** Must meet at least **3 of 10** criteria for approval.

---

## 🔐 Security & Access Control

### Authentication:
- JWT tokens valid for 24 hours
- Configurable via `JWT_EXPIRE_HOURS`
- Bearer token in Authorization header

### Role-Based Access Control (RBAC):

| Role | Permissions |
|------|-------------|
| **admin** | Full access + metrics endpoint |
| **lawyer** | Case management + tools + analysis |
| **viewer** | Read-only access to own cases |

### Rate Limiting:
- Default: 60 requests/minute per IP
- Configurable via `API_RATE_LIMIT`, `API_RATE_WINDOW`

### Data Security:
- All data encrypted in Supabase/PostgreSQL
- Prompt injection detection
- Audit trail for all operations
- CORS configured via SecurityConfig

---

## 🗂️ Data Storage

### Backend (Supabase/PostgreSQL):
- **Cases table** - Case metadata and status
- **Semantic memory** - pgvector for contextual search
- **Episodic memory** - Interaction history
- **Working memory** - Current agent context
- **Intake progress** - Questionnaire state per user

### Frontend (localStorage):
- Chat history per case
- User preferences
- Session state

### Cache (Redis):
- Session management
- Rate limiting state
- Temporary data

---

## 🔧 System Architecture

```
┌─────────────────────────────────────────┐
│          User Interfaces                │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Web UI  │ │Telegram │ │ Direct   │ │
│  │(Next.js)│ │  Bot    │ │   API    │ │
│  └────┬────┘ └────┬────┘ └─────┬────┘ │
└───────┼───────────┼────────────┼───────┘
        │           │            │
        └───────────┴────────────┘
                    │
        ┌───────────▼───────────────────┐
        │   FastAPI Backend (Railway)   │
        │                               │
        │  ┌─────────────────────────┐ │
        │  │   DI Container          │ │
        │  │  - MegaAgent            │ │
        │  │  - MemoryManager        │ │
        │  │  - LLM Router           │ │
        │  │  - Tool Registry        │ │
        │  └─────────────────────────┘ │
        └───────────┬───────────────────┘
                    │
        ┌───────────▼───────────────────┐
        │  Supabase/PostgreSQL + Redis  │
        └───────────────────────────────┘
```

---

## 📊 Typical Workflow

### For a New Client:

**Day 1: Initial Assessment**
```
1. /start in Telegram
2. /intake_start - Complete 8-block questionnaire (15-30 min)
3. /eb1_analyze - Receive analysis (score + recommendations)
```

**Day 2-3: Document Collection**
```
4. Upload supporting documents (PDFs via Telegram)
5. /generate_letter - Generate recommendation letter templates
6. Review and edit generated content
```

**Day 4-7: Case Development**
```
7. Work with lawyer via Web UI
8. Refine petition narrative
9. Finalize evidence package
10. Export complete USCIS-ready package
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| "Access denied" in Telegram | Add user_id to `TELEGRAM_ALLOWED_USERS` |
| "401 Unauthorized" API | Token expired - obtain new via `/auth/login` |
| "503 Service Unavailable" | Check backend status at `/health` |
| Bot not responding | Try `/start` again |
| Frontend not loading | Clear browser cache, check API connection |
| SSE stream disconnected | Reconnect - streams auto-resume |

---

## 📚 Additional Documentation

- **[Quick Start Guide](./QUICK_START_GUIDE.md)** - Choose your path and start in 2 minutes
- **[User Flow Diagrams](./USER_FLOW_DIAGRAM.md)** - Visual representations of user journeys
- **[Onboarding Cheatsheet](./USER_ONBOARDING_CHEATSHEET.md)** - Quick reference card
- **[Project Analysis](./PROJECT_ANALYSIS.md)** - Full system architecture
- **[README](../README.md)** - Installation and configuration

---

## 🌍 Supported Languages

- **Interface:** Russian (primary), English
- **Generated Documents:** English (USCIS requirement)
- **LLM Responses:** Multilingual based on user input

---

## 📞 Support & Resources

### GitHub Repositories:
- **Backend:** https://github.com/langgraphsystem/lawercase
- **Frontend:** https://github.com/langgraphsystem/eb1a-frontend
- **Branch:** `hardening/roadmap-v1`

### For Issues:
Create GitHub issues in the respective repository

### For Integrations:
Refer to API documentation and code examples in `/examples` directory

---

## 🚀 Next Steps

After completing initial assessment:

1. **Generate letters** - `/generate_letter` or via Web UI
2. **Collect evidence** - Upload documents systematically
3. **Review criteria** - Ensure 3+ criteria are strongly met
4. **Draft petition** - Use AI assistance for narrative
5. **Legal review** - Collaborate with immigration attorney
6. **Finalize package** - Export USCIS-ready PDF package

---

**Ready to begin? Choose your entry point above and start your EB-1A journey! 🎉**

---

*Version 1.0 | Last Updated: 2026-01-16 | Branch: hardening/roadmap-v1*
