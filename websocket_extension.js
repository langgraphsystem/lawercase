/**
 * WebSocket Extension for Document Monitor
 *
 * Add this script to index.html to enable WebSocket support:
 * <script src="websocket_extension.js"></script>
 *
 * Or copy-paste the code into index.html's <script> section
 */

// Extend DocumentMonitor with WebSocket support
(function() {
  'use strict';

  // Check if DocumentMonitor exists
  if (typeof DocumentMonitor === 'undefined') {
    console.error('DocumentMonitor class not found. Load this after index.html');
    return;
  }

  // Store original constructor
  const OriginalDocumentMonitor = DocumentMonitor;

  // Enhanced DocumentMonitor with WebSocket
  window.DocumentMonitor = class DocumentMonitorWS extends OriginalDocumentMonitor {
    constructor(threadId, options = {}) {
      super(threadId, options);

      // WebSocket properties
      this.useWebSocket = options.useWebSocket !== undefined ? options.useWebSocket : CONFIG.USE_WEBSOCKET;
      this.ws = null;
      this.wsReconnectAttempts = 0;
      this.wsMaxReconnectAttempts = 10;
      this.wsReconnectTimer = null;
    }

    // Override startPolling to use WebSocket
    async startPolling() {
      if (this.isPolling) {
        return;
      }

      this.isPolling = true;

      if (!this.hasStarted) {
        this.hasStarted = true;
        this.startTime = Date.now();
        UI.addLog('info', 'Starting real-time monitoring', 'DocumentMonitor');
      } else {
        if (!this.startTime) {
          this.startTime = Date.now();
        }
        UI.addLog('info', 'Resuming real-time monitoring', 'DocumentMonitor');
      }

      // Use WebSocket if enabled and not in mock mode
      if (this.useWebSocket && !this.mockMode) {
        this.connectWebSocket();
      } else {
        // Fall back to polling
        await this.poll();
      }
    }

    // Override stopPolling
    stopPolling() {
      super.stopPolling();
      this.disconnectWebSocket();
    }

    // WebSocket connection
    connectWebSocket() {
      try {
        const wsUrl = API_ENDPOINTS.websocket(this.threadId);
        console.log('[WebSocket] Connecting to:', wsUrl);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected');
          this.wsReconnectAttempts = 0;
          UI.addLog('success', '🔌 WebSocket connected - receiving instant updates', 'WebSocket');
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('[WebSocket] Parse error:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
        };

        this.ws.onclose = () => {
          console.log('[WebSocket] Connection closed');
          this.ws = null;

          // Auto-reconnect if still polling
          if (this.isPolling && this.wsReconnectAttempts < this.wsMaxReconnectAttempts) {
            this.wsReconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.wsReconnectAttempts), 30000);

            UI.addLog('warning', `Reconnecting WebSocket in ${Math.round(delay/1000)}s (attempt ${this.wsReconnectAttempts})`, 'WebSocket');

            this.wsReconnectTimer = setTimeout(() => {
              this.connectWebSocket();
            }, delay);
          } else if (this.wsReconnectAttempts >= this.wsMaxReconnectAttempts) {
            UI.addLog('error', 'WebSocket reconnect failed. Falling back to polling.', 'WebSocket');
            this.useWebSocket = false;
            this.poll(); // Fall back to polling
          }
        };

      } catch (error) {
        console.error('[WebSocket] Connection failed:', error);
        UI.addLog('error', 'WebSocket unavailable. Using polling instead.', 'DocumentMonitor');
        this.useWebSocket = false;
        this.poll();
      }
    }

    disconnectWebSocket() {
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }

      if (this.wsReconnectTimer) {
        clearTimeout(this.wsReconnectTimer);
        this.wsReconnectTimer = null;
      }
    }

    handleWebSocketMessage(message) {
      console.log('[WebSocket] Message:', message.type);

      switch (message.type) {
        case 'connected':
          // Connection confirmed
          break;

        case 'initial_state':
          // Load initial state
          if (message.state) {
            const data = this.convertStateToPreviewFormat(message.state);
            this.updateUI(data);
          }
          break;

        case 'workflow_update':
        case 'section_update':
          // Fetch latest state
          this.fetchAndUpdateUI();
          break;

        case 'log_entry':
          // Add new log
          if (message.log) {
            UI.updateLogs([message.log]);
          }
          break;

        case 'status_change':
          this.handleStatusChange(message);
          break;

        case 'progress_update':
          if (message.completed !== undefined) {
            UI.updateStatistics({
              completed_sections: message.completed,
              total_sections: message.total,
              progress_percentage: message.percentage,
            });
          }
          break;

        case 'error':
          UI.addLog('error', message.error_message || 'Error occurred', 'System');
          break;

        case 'pong':
          // Keep-alive response
          break;

        default:
          console.log('[WebSocket] Unknown type:', message.type);
      }
    }

    handleStatusChange(message) {
      if (message.status === 'completed') {
        this.onComplete({ status: 'completed' });
        this.stopPolling();
      } else if (message.status === 'error') {
        this.onError({ status: 'error' });
        this.stopPolling();
      } else if (message.status === 'paused') {
        UI.updateControlButtons('paused');
      }
    }

    async fetchAndUpdateUI() {
      try {
        const data = await this.fetchStatus();
        this.updateUI(data);
      } catch (error) {
        console.error('Failed to fetch state:', error);
      }
    }

    convertStateToPreviewFormat(state) {
      return {
        thread_id: state.thread_id,
        status: state.status,
        sections: state.sections || [],
        exhibits: state.exhibits || [],
        metadata: this.calculateMetadata(state),
        logs: state.logs || [],
      };
    }

    calculateMetadata(state) {
      const sections = state.sections || [];
      const completed = sections.filter(s => s.status === 'completed').length;
      const total = sections.length;
      const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

      const startedAt = state.started_at ? new Date(state.started_at) : null;
      const elapsed = startedAt ? Math.floor((Date.now() - startedAt.getTime()) / 1000) : 0;

      const totalTokens = sections.reduce((sum, s) => sum + (s.tokens_used || 0), 0);

      return {
        total_sections: total,
        completed_sections: completed,
        progress_percentage: percentage,
        elapsed_time: elapsed,
        estimated_remaining: Math.max(0, (total - completed) * 3), // 3 sec avg per section
        total_tokens: totalTokens,
        estimated_cost: totalTokens * 0.00001,
      };
    }
  };

  console.log('[WebSocket] DocumentMonitor enhanced with WebSocket support');

})();
