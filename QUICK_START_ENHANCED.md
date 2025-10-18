# 🚀 Enhanced Document Monitor - Quick Start Guide

## New Features Added

### 1. Mock FastAPI Server (`mock_server.py`)

**Features:**
- ✅ Full simulation of document generation workflow
- ✅ Progressive section generation (5 sections, ~30 seconds total)
- ✅ **Human-in-the-loop approval** (awards section requires approval)
- ✅ **WebSocket real-time updates** (no polling needed)
- ✅ File upload simulation
- ✅ Pause/Resume functionality
- ✅ PDF download (mock)

**Start the server:**

```bash
# Install dependencies first
pip install fastapi uvicorn websockets python-multipart

# Run the mock server
python mock_server.py
```

Server will start on `http://localhost:8000`

### 2. Monitor Extensions (`monitor_extensions.js`)

**Features:**
- ✅ **WebSocket Manager** - Real-time updates without polling
- ✅ **Human-in-the-loop UI** - Beautiful approval modal
- ✅ **localStorage Persistence** - Auto-resume sessions
- ✅ **Session Management** - Multiple document sessions

**Usage:**

Include in your HTML after main script:

```html
<script src="monitor_extensions.js"></script>
```

Or add to existing index.html before closing `</body>`:

```html
<script src="monitor_extensions.js"></script>
```

---

## 🎯 Complete Test Workflow (5 minutes)

### Step 1: Start Mock Server

```bash
python mock_server.py
```

You should see:

```
════════════════════════════════════════════════════════════════════════════
🚀 Starting Mock Document Monitor API Server
════════════════════════════════════════════════════════════════════════════

📍 API Documentation:  http://localhost:8000/docs
🎯 Monitor Interface:  http://localhost:8000/monitor/index.html

Features:
  ✅ Progressive document generation (5 sections)
  ✅ Human-in-the-loop approval (awards section)
  ✅ WebSocket real-time updates
  ✅ File upload simulation
  ✅ Pause/Resume functionality
  ✅ PDF download (mock)

Press Ctrl+C to stop
════════════════════════════════════════════════════════════════════════════
```

### Step 2: Open Monitor Interface

Open your browser to: `http://localhost:8000/monitor/index.html`

**OR** add the extensions to index.html:

1. Open `index.html` in editor
2. Before closing `</body>`, add:

```html
<script src="monitor_extensions.js"></script>
</body>
```

3. Update CONFIG:

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000/api',
  POLL_INTERVAL: 2000,
  MAX_POLL_ERRORS: 5,
  MOCK_MODE: false,  // Set to false to use mock server
};
```

### Step 3: Start Generation

1. Click **"Start Generation"** button
2. Monitor will connect via **WebSocket** (check console: "WebSocket Connected")
3. Watch sections generate progressively

**Timeline:**
- `0s` - Introduction starts
- `5s` - Introduction completes
- `7s` - Background starts
- `12s` - Background completes
- `14s` - **Awards section starts** → **APPROVAL REQUIRED**
- `19s` - **Modal appears!**

### Step 4: Test Human-in-the-Loop

When the **Approval Modal** appears:

![Approval Modal](conceptual image)

**Option A: Approve**
1. Review the generated content in preview
2. Optionally add comments
3. Click **"✅ Approve & Continue"**
4. Generation continues automatically

**Option B: Reject**
1. **Must add comments** (required for rejection)
2. Example: "Please add more details about award criteria"
3. Click **"❌ Reject & Regenerate"**
4. Section will be regenerated (in production)

### Step 5: Test Other Features

**Upload Exhibit:**
1. Enter ID: `2.1.A`
2. Choose any file
3. Click "Upload"
4. File appears in sidebar

**Pause/Resume:**
1. Click "Pause" during generation
2. Generation stops
3. Click "Resume" to continue

**WebSocket Real-time:**
- Watch console: `[WebSocket] Received update`
- No polling requests in Network tab!

### Step 6: Test Session Persistence

1. Refresh the page during generation
2. **Session auto-resumes!** (from localStorage)
3. Monitor reconnects and continues

---

## 📡 WebSocket vs Polling Comparison

### Polling Mode (OLD)

```
Frontend                    Backend
   │                           │
   ├──── GET /preview ────────►│
   │◄──── Response ────────────┤
   │                           │
   │ (wait 2 seconds)          │
   │                           │
   ├──── GET /preview ────────►│
   │◄──── Response ────────────┤
   │                           │
   │ (wait 2 seconds)          │
   │                           │
   └──── ... continuous polling
```

**Drawbacks:**
- 2-second delay for updates
- Constant HTTP overhead
- Server load from polling
- Network inefficiency

### WebSocket Mode (NEW)

```
Frontend                    Backend
   │                           │
   ├──── WS Connect ──────────►│
   │◄──── Connected ───────────┤
   │                           │
   │◄──── Update (instant!) ───┤
   │◄──── Update (instant!) ───┤
   │◄──── Update (instant!) ───┤
   │                           │
   │ (ping/pong keep-alive)    │
   │                           │
   └──── ... stays connected
```

**Benefits:**
- ✅ **Instant updates** (no delay)
- ✅ **Bi-directional** communication
- ✅ **Lower overhead** (one connection)
- ✅ **Better UX** (real-time feel)

---

## 🎨 Human-in-the-Loop UI

### Modal Features

**Design:**
- Clean, professional modal dialog
- Darkened overlay with blur effect
- Preview pane with document styles
- Comment textarea for feedback
- Two-button approval system

**Accessibility:**
- Keyboard shortcuts (Escape to close)
- Focus management (auto-focus on approve)
- ARIA labels for screen readers
- Tab navigation support

**Workflow:**
1. Backend sets `status: "pending_approval"`
2. Frontend detects and fetches approval details
3. Modal appears with section preview
4. User reviews and decides
5. Approval/rejection sent to backend
6. Generation continues/regenerates

**Backend Integration:**

```python
# In your workflow node
if section_needs_approval(section_id):
    state_store.pending_approvals[thread_id] = {
        "section_id": section_id,
        "section_name": section_name,
        "content_html": generated_html,
    }

    # Wait for approval
    while thread_id in state_store.pending_approvals:
        await asyncio.sleep(1)
```

---

## 💾 localStorage Persistence

### Data Stored

```javascript
// Active thread ID
localStorage.monitor_active_thread = "thread-abc-123"

// All sessions
localStorage.monitor_sessions = {
  "thread-abc-123": {
    threadId: "thread-abc-123",
    caseId: "case-001",
    startedAt: "2025-01-18T10:30:00Z",
    lastAccessed: "2025-01-18T10:35:00Z"
  },
  "thread-def-456": { ... }
}

// User settings
localStorage.monitor_settings = {
  useWebSocket: true,
  pollInterval: 2000,
  darkMode: false,
  autoSaveProgress: true
}
```

### Session Management

**View Sessions:**

```javascript
// In browser console
StorageManager.getSessions()
```

**Resume Session:**

```javascript
StorageManager.saveActiveThread('thread-abc-123')
location.reload()
```

**Clear All:**

```javascript
localStorage.clear()
```

---

## 🛠️ Integration Guide

### Option 1: Include Extensions in index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <!-- ... existing head ... -->
</head>
<body>
  <!-- ... existing HTML ... -->

  <script>
    // ... existing JavaScript ...
  </script>

  <!-- ADD THIS -->
  <script src="monitor_extensions.js"></script>
</body>
</html>
```

### Option 2: Merge into Single File

Copy contents of `monitor_extensions.js` and append to `<script>` section in index.html.

### Option 3: Load Dynamically

```javascript
// At end of existing script
const script = document.createElement('script');
script.src = 'monitor_extensions.js';
document.body.appendChild(script);
```

---

## 🧪 Testing Checklist

- [ ] **Mock Server**
  - [ ] Server starts without errors
  - [ ] API docs accessible at `/docs`
  - [ ] Monitor accessible at `/monitor/index.html`

- [ ] **WebSocket**
  - [ ] Connection establishes (check console)
  - [ ] Real-time updates visible (no polling)
  - [ ] Reconnection works after disconnect
  - [ ] Falls back to polling if WS fails

- [ ] **Human-in-the-loop**
  - [ ] Modal appears for awards section
  - [ ] Content preview renders correctly
  - [ ] Approve flow completes generation
  - [ ] Reject flow requires comments
  - [ ] Modal closes on Escape key

- [ ] **localStorage**
  - [ ] Session saves on start
  - [ ] Page refresh resumes session
  - [ ] Settings persist across reloads
  - [ ] Multiple sessions can be saved

- [ ] **File Upload**
  - [ ] File selection works
  - [ ] Upload progress shows
  - [ ] Exhibit appears in sidebar
  - [ ] Multiple uploads supported

- [ ] **Pause/Resume**
  - [ ] Pause stops generation
  - [ ] Resume continues from pause
  - [ ] State persists during pause

- [ ] **Download PDF**
  - [ ] Button enabled when complete
  - [ ] PDF downloads successfully
  - [ ] Filename includes thread ID

---

## 🐛 Troubleshooting

### Issue: WebSocket won't connect

**Symptoms:**
- Console shows `[WebSocket] Error`
- Falls back to polling

**Solutions:**
1. Check mock server is running: `http://localhost:8000/docs`
2. Check CORS settings (should be enabled)
3. Try different port if 8000 is in use
4. Check browser WebSocket support

### Issue: Modal doesn't appear

**Symptoms:**
- Awards section completes without approval
- No modal shown

**Solutions:**
1. Check console for JavaScript errors
2. Verify `monitor_extensions.js` is loaded
3. Check if `hitlUI` is initialized: `window.HumanInTheLoopUI`
4. Verify backend returns `status: "pending_approval"`

### Issue: Session doesn't resume

**Symptoms:**
- Page refresh loses progress
- No auto-resume

**Solutions:**
1. Check localStorage: `localStorage.monitor_active_thread`
2. Verify `monitor_extensions.js` is loaded
3. Check console for errors during init
4. Try clearing localStorage and restart

### Issue: File upload fails

**Symptoms:**
- Upload button doesn't work
- Error in console

**Solutions:**
1. Check file size (mock server has limits)
2. Verify FormData is supported
3. Check network tab for 400/500 errors
4. Ensure thread ID is valid

---

## 📊 Performance

### WebSocket Performance

| Metric | Polling | WebSocket |
|--------|---------|-----------|
| Update latency | 0-2000ms | <100ms |
| Network requests | 30/min | 1 connection |
| Server load | High | Low |
| Battery impact | High | Low |
| Bandwidth | ~1MB/min | ~10KB/min |

### localStorage Impact

- Storage used: ~5KB per session
- Max sessions: ~1000 (before hitting 5MB limit)
- Read/write: <1ms
- No network overhead

---

## 🎓 Advanced Usage

### Custom WebSocket URL

```javascript
// In monitor_extensions.js, modify:
const wsUrl = `wss://your-server.com/ws/document/${this.threadId}`;
```

### Disable Auto-resume

```javascript
StorageManager.saveSettings({ autoSaveProgress: false });
```

### Change Approval Timeout

```javascript
// Add to backend workflow
timeout = 300  # 5 minutes
start_time = time.time()

while thread_id in pending_approvals:
    if time.time() - start_time > timeout:
        # Auto-reject on timeout
        break
    await asyncio.sleep(1)
```

### Export Session Data

```javascript
function exportSessions() {
  const sessions = StorageManager.getSessions();
  const blob = new Blob([JSON.stringify(sessions, null, 2)], {
    type: 'application/json'
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'monitor-sessions.json';
  a.click();
}
```

---

## 📚 API Reference

### WebSocketManager

```javascript
const wsManager = new WebSocketManager(threadId, (data) => {
  console.log('Update received:', data);
});

wsManager.connect();
wsManager.disconnect();
wsManager.isConnected(); // boolean
```

### StorageManager

```javascript
// Thread management
StorageManager.saveActiveThread(threadId);
StorageManager.getActiveThread();
StorageManager.clearActiveThread();

// Session management
StorageManager.saveSession(threadId, caseId, startedAt);
StorageManager.getSessions();
StorageManager.getSession(threadId);
StorageManager.deleteSession(threadId);

// Settings
StorageManager.saveSettings({ useWebSocket: true });
StorageManager.getSettings();
```

### HumanInTheLoopUI

```javascript
hitlUI.show(threadId, sectionId, sectionName, contentHtml);
hitlUI.close();
// handleApprove() and handleReject() called automatically
```

---

## 🚀 Next Steps

1. **English UI**: Update all text in index.html to English (see translation guide)
2. **Production Deploy**: Use real FastAPI backend instead of mock
3. **Authentication**: Add JWT auth to WebSocket and API
4. **Database**: Store sessions in PostgreSQL instead of localStorage
5. **Analytics**: Track approval rates, generation times, etc.

---

## 📞 Support

For issues or questions:

1. Check this guide first
2. Review `mock_server.py` code for backend logic
3. Review `monitor_extensions.js` for frontend logic
4. Check browser console for errors
5. Check network tab for failed requests

**Files:**
- `mock_server.py` - Full-featured mock backend
- `monitor_extensions.js` - WebSocket, HITL, localStorage
- `index.html` - Main monitor UI
- `QUICK_START_ENHANCED.md` - This guide

---

**Ready to test!** 🎉

Start with: `python mock_server.py`
