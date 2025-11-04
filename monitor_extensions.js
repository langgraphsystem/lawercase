/**
 * Monitor Extensions
 *
 * Additional features for Document Monitor:
 * - WebSocket support for real-time updates
 * - Human-in-the-loop UI (approval modals)
 * - localStorage persistence
 * - English localization
 *
 * Include this script AFTER the main index.html script section
 */

/* ═════════════════════════════════════════════════════════════════════════
   WEBSOCKET MANAGER
   ═══════════════════════════════════════════════════════════════════════ */

class WebSocketManager {
  constructor(threadId, onUpdate) {
    this.threadId = threadId;
    this.onUpdate = onUpdate;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
    this.pingInterval = null;
  }

  connect() {
    const wsUrl = `ws://localhost:8000/ws/document/${this.threadId}`;
    console.log(`[WebSocket] Connecting to ${wsUrl}`);

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
      this.reconnectAttempts = 0;
      UI.addLog('success', 'Real-time connection established', 'WebSocket');

      // Start ping-pong to keep connection alive
      this.pingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 30000); // Every 30 seconds
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] Received update:', data);

        // Call update handler
        if (this.onUpdate) {
          this.onUpdate(data);
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      UI.addLog('error', 'WebSocket connection error', 'WebSocket');
    };

    this.ws.onclose = () => {
      console.log('[WebSocket] Disconnected');

      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }

      // Attempt reconnection
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`[WebSocket] Reconnecting (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

        setTimeout(() => {
          this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
      } else {
        UI.addLog('error', 'WebSocket disconnected. Falling back to polling.', 'WebSocket');
        // Fall back to polling
        if (currentMonitor) {
          currentMonitor.useWebSocket = false;
          currentMonitor.startPolling();
        }
      }
    };
  }

  disconnect() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

/* ═════════════════════════════════════════════════════════════════════════
   LOCALSTORAGE PERSISTENCE
   ═══════════════════════════════════════════════════════════════════════ */

const StorageManager = {
  KEYS: {
    ACTIVE_THREAD: 'monitor_active_thread',
    SESSIONS: 'monitor_sessions',
    SETTINGS: 'monitor_settings',
  },

  saveActiveThread(threadId) {
    localStorage.setItem(this.KEYS.ACTIVE_THREAD, threadId);
  },

  getActiveThread() {
    return localStorage.getItem(this.KEYS.ACTIVE_THREAD);
  },

  clearActiveThread() {
    localStorage.removeItem(this.KEYS.ACTIVE_THREAD);
  },

  saveSession(threadId, caseId, startedAt) {
    const sessions = this.getSessions();
    sessions[threadId] = {
      threadId,
      caseId,
      startedAt,
      lastAccessed: new Date().toISOString(),
    };
    localStorage.setItem(this.KEYS.SESSIONS, JSON.stringify(sessions));
  },

  getSessions() {
    const data = localStorage.getItem(this.KEYS.SESSIONS);
    return data ? JSON.parse(data) : {};
  },

  getSession(threadId) {
    const sessions = this.getSessions();
    return sessions[threadId] || null;
  },

  deleteSession(threadId) {
    const sessions = this.getSessions();
    delete sessions[threadId];
    localStorage.setItem(this.KEYS.SESSIONS, JSON.stringify(sessions));
  },

  saveSettings(settings) {
    const currentSettings = this.getSettings();
    const newSettings = { ...currentSettings, ...settings };
    localStorage.setItem(this.KEYS.SETTINGS, JSON.stringify(newSettings));
  },

  getSettings() {
    const data = localStorage.getItem(this.KEYS.SETTINGS);
    return data ? JSON.parse(data) : {
      useWebSocket: true,
      pollInterval: 2000,
      darkMode: false,
      autoSaveProgress: true,
    };
  },
};

/* ═════════════════════════════════════════════════════════════════════════
   HUMAN-IN-THE-LOOP UI
   ═══════════════════════════════════════════════════════════════════════ */

class HumanInTheLoopUI {
  constructor() {
    this.currentApproval = null;
    this.createModal();
  }

  createModal() {
    // Create modal HTML
    const modalHTML = `
      <div id="approval-modal" class="modal hidden" role="dialog" aria-labelledby="modal-title" aria-modal="true">
        <div class="modal-overlay" id="modal-overlay"></div>
        <div class="modal-container">
          <div class="modal-header">
            <h2 id="modal-title">Human Approval Required</h2>
            <button class="modal-close" id="modal-close" aria-label="Close modal">×</button>
          </div>

          <div class="modal-body">
            <div class="approval-info">
              <p><strong>Section:</strong> <span id="approval-section-name"></span></p>
              <p><strong>Status:</strong> Requires your review before proceeding</p>
            </div>

            <div class="approval-preview" id="approval-preview">
              <!-- Content preview will be inserted here -->
            </div>

            <div class="approval-feedback">
              <label for="approval-comments">Comments (optional):</label>
              <textarea
                id="approval-comments"
                rows="4"
                placeholder="Add any feedback or suggested changes..."
              ></textarea>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-outline" id="btn-reject">
              ❌ Reject & Regenerate
            </button>
            <button class="btn btn-primary" id="btn-approve">
              ✅ Approve & Continue
            </button>
          </div>
        </div>
      </div>
    `;

    // Add to document
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add modal styles
    this.addModalStyles();

    // Bind events
    this.bindEvents();
  }

  addModalStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: opacity 0.3s ease;
      }

      .modal.hidden {
        opacity: 0;
        pointer-events: none;
      }

      .modal-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(4px);
      }

      .modal-container {
        position: relative;
        background: var(--color-bg-white);
        border-radius: 12px;
        box-shadow: var(--shadow-xl);
        max-width: 800px;
        width: 90%;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        animation: modalSlideIn 0.3s ease;
      }

      @keyframes modalSlideIn {
        from {
          transform: translateY(-50px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }

      .modal-header {
        padding: var(--spacing-lg);
        border-bottom: 1px solid var(--color-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .modal-header h2 {
        margin: 0;
        font-size: 20px;
        color: var(--color-text-dark);
      }

      .modal-close {
        background: none;
        border: none;
        font-size: 32px;
        line-height: 1;
        color: var(--color-text-medium);
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        transition: background var(--transition-fast);
      }

      .modal-close:hover {
        background: var(--color-bg-gray);
        color: var(--color-text-dark);
      }

      .modal-body {
        padding: var(--spacing-lg);
        overflow-y: auto;
        flex: 1;
      }

      .approval-info {
        background: var(--color-bg-light);
        padding: var(--spacing-md);
        border-radius: 8px;
        margin-bottom: var(--spacing-lg);
      }

      .approval-info p {
        margin: var(--spacing-sm) 0;
        font-size: 14px;
      }

      .approval-preview {
        background: white;
        border: 2px solid var(--color-border);
        border-radius: 8px;
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-lg);
        max-height: 400px;
        overflow-y: auto;
        font-family: var(--font-document);
        font-size: 11pt;
        line-height: 1.5;
      }

      .approval-feedback label {
        display: block;
        font-weight: 600;
        margin-bottom: var(--spacing-sm);
        font-size: 14px;
      }

      .approval-feedback textarea {
        width: 100%;
        padding: var(--spacing-md);
        border: 1px solid var(--color-border);
        border-radius: 6px;
        font-family: var(--font-ui);
        font-size: 14px;
        resize: vertical;
      }

      .approval-feedback textarea:focus {
        outline: none;
        border-color: var(--color-primary);
        box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
      }

      .modal-footer {
        padding: var(--spacing-lg);
        border-top: 1px solid var(--color-border);
        display: flex;
        gap: var(--spacing-md);
        justify-content: flex-end;
      }

      .modal-footer .btn {
        min-width: 150px;
      }
    `;
    document.head.appendChild(style);
  }

  bindEvents() {
    const modal = document.getElementById('approval-modal');
    const overlay = document.getElementById('modal-overlay');
    const closeBtn = document.getElementById('modal-close');
    const approveBtn = document.getElementById('btn-approve');
    const rejectBtn = document.getElementById('btn-reject');

    // Close on overlay click
    overlay.addEventListener('click', () => this.close());

    // Close on X button
    closeBtn.addEventListener('click', () => this.close());

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        this.close();
      }
    });

    // Approve button
    approveBtn.addEventListener('click', () => this.handleApprove());

    // Reject button
    rejectBtn.addEventListener('click', () => this.handleReject());
  }

  async show(threadId, sectionId, sectionName, contentHtml) {
    this.currentApproval = { threadId, sectionId };

    // Update modal content
    document.getElementById('approval-section-name').textContent = sectionName;
    document.getElementById('approval-preview').innerHTML = contentHtml;
    document.getElementById('approval-comments').value = '';

    // Show modal
    const modal = document.getElementById('approval-modal');
    modal.classList.remove('hidden');

    // Focus on approve button
    document.getElementById('btn-approve').focus();

    UI.addLog('warning', `Section "${sectionName}" requires approval`, 'System');
  }

  close() {
    const modal = document.getElementById('approval-modal');
    modal.classList.add('hidden');
  }

  async handleApprove() {
    if (!this.currentApproval) return;

    const { threadId } = this.currentApproval;
    const comments = document.getElementById('approval-comments').value;

    try {
      const response = await fetch(`/api/approve/${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approved: true,
          comments: comments || null,
        }),
      });

      if (!response.ok) throw new Error('Approval failed');

      const data = await response.json();
      UI.addLog('success', data.message, 'User');

      this.close();
      this.currentApproval = null;

    } catch (error) {
      console.error('Approval error:', error);
      UI.addLog('error', 'Failed to submit approval', 'System');
    }
  }

  async handleReject() {
    if (!this.currentApproval) return;

    const { threadId } = this.currentApproval;
    const comments = document.getElementById('approval-comments').value;

    if (!comments) {
      alert('Please provide feedback for rejection');
      document.getElementById('approval-comments').focus();
      return;
    }

    try {
      const response = await fetch(`/api/approve/${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approved: false,
          comments,
        }),
      });

      if (!response.ok) throw new Error('Rejection failed');

      const data = await response.json();
      UI.addLog('warning', data.message, 'User');

      this.close();
      this.currentApproval = null;

    } catch (error) {
      console.error('Rejection error:', error);
      UI.addLog('error', 'Failed to submit rejection', 'System');
    }
  }
}

// Initialize HITL UI
const hitlUI = new HumanInTheLoopUI();

/* ═════════════════════════════════════════════════════════════════════════
   EXTENDED DOCUMENT MONITOR (WITH WEBSOCKET)
   ═══════════════════════════════════════════════════════════════════════ */

// Extend the existing DocumentMonitor class
if (typeof DocumentMonitor !== 'undefined') {
  const originalConstructor = DocumentMonitor;

  DocumentMonitor = function(threadId, options = {}) {
    originalConstructor.call(this, threadId, options);

    this.useWebSocket = options.useWebSocket !== false; // Default: true
    this.wsManager = null;

    // Save settings
    const settings = StorageManager.getSettings();
    this.useWebSocket = settings.useWebSocket;
    this.pollInterval = settings.pollInterval || this.pollInterval;
  };

  // Copy prototype
  DocumentMonitor.prototype = Object.create(originalConstructor.prototype);
  DocumentMonitor.prototype.constructor = DocumentMonitor;

  // Override startPolling to use WebSocket if available
  const originalStartPolling = DocumentMonitor.prototype.startPolling;
  DocumentMonitor.prototype.startPolling = async function() {
    if (this.useWebSocket) {
      this.startWebSocket();
    } else {
      await originalStartPolling.call(this);
    }
  };

  // Add WebSocket method
  DocumentMonitor.prototype.startWebSocket = function() {
    UI.addLog('info', 'Starting WebSocket connection...', 'DocumentMonitor');

    this.wsManager = new WebSocketManager(this.threadId, (data) => {
      this.updateUI(data);

      // Check for pending approval
      if (data.status === 'pending_approval') {
        this.handlePendingApproval();
      }

      // Auto-stop on completion
      if (data.status === 'completed') {
        this.stopWebSocket();
        this.onComplete(data);
      } else if (data.status === 'error') {
        this.stopWebSocket();
        this.onError(data);
      }
    });

    this.wsManager.connect();
  };

  DocumentMonitor.prototype.stopWebSocket = function() {
    if (this.wsManager) {
      this.wsManager.disconnect();
      this.wsManager = null;
    }
  };

  DocumentMonitor.prototype.handlePendingApproval = async function() {
    try {
      const response = await fetch(`/api/pending-approval/${this.threadId}`);
      if (!response.ok) return;

      const approval = await response.json();

      hitlUI.show(
        this.threadId,
        approval.section_id,
        approval.section_name,
        approval.content_html
      );

    } catch (error) {
      console.error('Failed to fetch pending approval:', error);
    }
  };

  // Override stopPolling to also stop WebSocket
  const originalStopPolling = DocumentMonitor.prototype.stopPolling;
  DocumentMonitor.prototype.stopPolling = function() {
    this.stopWebSocket();
    originalStopPolling.call(this);
  };
}

/* ═════════════════════════════════════════════════════════════════════════
   SESSION MANAGEMENT UI
   ═══════════════════════════════════════════════════════════════════════ */

function showSessionManager() {
  const sessions = StorageManager.getSessions();
  const sessionKeys = Object.keys(sessions);

  if (sessionKeys.length === 0) {
    alert('No saved sessions found');
    return;
  }

  let html = '<h3>Saved Sessions</h3><ul>';
  sessionKeys.forEach(threadId => {
    const session = sessions[threadId];
    const startedDate = new Date(session.startedAt).toLocaleString();
    html += `
      <li>
        <strong>${session.caseId}</strong><br>
        Thread: ${threadId}<br>
        Started: ${startedDate}<br>
        <button onclick="resumeSession('${threadId}')">Resume</button>
        <button onclick="deleteSession('${threadId}')">Delete</button>
      </li>
    `;
  });
  html += '</ul>';

  // Show in a simple dialog (could be enhanced with a modal)
  const container = document.createElement('div');
  container.innerHTML = html;
  container.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    z-index: 2000;
    max-width: 500px;
    max-height: 80vh;
    overflow-y: auto;
  `;

  document.body.appendChild(container);

  // Add close button
  const closeBtn = document.createElement('button');
  closeBtn.textContent = 'Close';
  closeBtn.onclick = () => container.remove();
  container.appendChild(closeBtn);
}

function resumeSession(threadId) {
  StorageManager.saveActiveThread(threadId);
  location.reload();
}

function deleteSessionUI(threadId) {
  if (confirm('Delete this session?')) {
    StorageManager.deleteSession(threadId);
    showSessionManager();
  }
}

/* ═════════════════════════════════════════════════════════════════════════
   AUTO-INITIALIZATION
   ═══════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  // Check for active session
  const activeThread = StorageManager.getActiveThread();
  if (activeThread) {
    const session = StorageManager.getSession(activeThread);
    if (session) {
      console.log('[Storage] Found active session:', session);
      UI.addLog('info', `Resuming session for ${session.caseId}`, 'System');

      // Auto-resume monitoring
      currentMonitor = new DocumentMonitor(activeThread, {
        useWebSocket: true,
      });
      currentMonitor.startPolling();
    }
  }

  // Apply saved settings
  const settings = StorageManager.getSettings();
  if (settings.darkMode) {
    document.body.classList.add('dark-mode');
  }

  console.log('[Monitor Extensions] Loaded successfully');
  console.log('Features enabled:');
  console.log('  ✅ WebSocket real-time updates');
  console.log('  ✅ Human-in-the-loop approval UI');
  console.log('  ✅ localStorage session persistence');
});

// Export for global access
window.StorageManager = StorageManager;
window.HumanInTheLoopUI = hitlUI;
window.WebSocketManager = WebSocketManager;
