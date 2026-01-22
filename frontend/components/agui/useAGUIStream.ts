/**
 * useAGUIStream - Custom React hook for AG-UI SSE streaming
 *
 * Provides real-time streaming of AG-UI events from the backend.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AGUIEvent, AGUIRunRequest, EventType } from './types';

export interface UseAGUIStreamOptions {
  /** Base URL for the API (default: '') */
  baseUrl?: string;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** Event handlers */
  onEvent?: (event: AGUIEvent) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export interface UseAGUIStreamReturn {
  /** Current connection status */
  isConnected: boolean;
  /** Loading state */
  isLoading: boolean;
  /** Last error */
  error: Error | null;
  /** All received events */
  events: AGUIEvent[];
  /** Accumulated text content from TEXT_MESSAGE_CONTENT events */
  streamedText: string;
  /** Current workflow step */
  currentStep: string | null;
  /** Start streaming a workflow */
  startWorkflow: (request: AGUIRunRequest) => void;
  /** Stop streaming */
  stopStream: () => void;
  /** Clear all events */
  clearEvents: () => void;
}

export function useAGUIStream(options: UseAGUIStreamOptions = {}): UseAGUIStreamReturn {
  const {
    baseUrl = '',
    autoReconnect = false,
    reconnectDelay = 3000,
    onEvent,
    onError,
    onConnect,
    onDisconnect,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [events, setEvents] = useState<AGUIEvent[]>([]);
  const [streamedText, setStreamedText] = useState('');
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (event: AGUIEvent) => {
      setEvents((prev) => [...prev, event]);

      // Handle specific event types
      switch (event.type) {
        case EventType.TEXT_MESSAGE_CONTENT:
          if (event.delta) {
            setStreamedText((prev) => prev + event.delta);
          }
          break;
        case EventType.STEP_STARTED:
          setCurrentStep(event.step_name || null);
          break;
        case EventType.STEP_FINISHED:
          // Keep step visible until next one starts
          break;
        case EventType.RUN_FINISHED:
          setIsLoading(false);
          break;
        case EventType.RUN_ERROR:
          setIsLoading(false);
          setError(new Error(event.error || 'Unknown error'));
          break;
      }

      onEvent?.(event);
    },
    [onEvent]
  );

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsConnected(false);
    setIsLoading(false);
    onDisconnect?.();
  }, [onDisconnect]);

  const startWorkflow = useCallback(
    async (request: AGUIRunRequest) => {
      // Stop any existing stream
      stopStream();

      setIsLoading(true);
      setError(null);
      setStreamedText('');
      setCurrentStep(null);

      try {
        // Use fetch with SSE for POST requests
        abortControllerRef.current = new AbortController();

        const response = await fetch(`${baseUrl}/agui/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify(request),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        setIsConnected(true);
        onConnect?.();

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          let currentEventType = '';
          let currentData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6);
              if (currentData) {
                try {
                  const event = JSON.parse(currentData) as AGUIEvent;
                  handleEvent(event);
                } catch (e) {
                  console.warn('Failed to parse SSE event:', currentData);
                }
              }
              currentEventType = '';
              currentData = '';
            }
          }
        }

        setIsConnected(false);
        setIsLoading(false);
        onDisconnect?.();
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          // Intentional abort, not an error
          return;
        }
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        setIsLoading(false);
        setIsConnected(false);
        onError?.(error);
      }
    },
    [baseUrl, handleEvent, onConnect, onDisconnect, onError, stopStream]
  );

  const clearEvents = useCallback(() => {
    setEvents([]);
    setStreamedText('');
    setCurrentStep(null);
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  return {
    isConnected,
    isLoading,
    error,
    events,
    streamedText,
    currentStep,
    startWorkflow,
    stopStream,
    clearEvents,
  };
}

export default useAGUIStream;
