# AG-UI React Components

React components for integrating with the AG-UI (Agent-User Interaction) protocol.

## Components

### `useAGUIStream`

Custom hook for SSE (Server-Sent Events) streaming from AG-UI endpoints.

```tsx
import { useAGUIStream, EventType } from './components/agui';

function MyComponent() {
  const {
    isConnected,
    isLoading,
    error,
    events,
    streamedText,
    currentStep,
    startWorkflow,
    stopStream,
    clearEvents,
  } = useAGUIStream({
    baseUrl: '/api',
    onEvent: (event) => {
      if (event.type === EventType.VALIDATION_REQUIRED) {
        // Show validation dialog
      }
    },
    onError: (error) => console.error(error),
  });

  const handleStart = () => {
    startWorkflow({
      case_id: 'case-123',
      operation: 'intake_questionnaire',
    });
  };

  return (
    <div>
      <button onClick={handleStart}>Start Intake</button>
      <pre>{streamedText}</pre>
    </div>
  );
}
```

### `IntakeProgress`

Displays real-time progress during the EB-1A intake questionnaire.

```tsx
import { IntakeProgress } from './components/agui';

function IntakePage() {
  return (
    <IntakeProgress
      caseId="case-123"
      baseUrl="/api"
      onComplete={() => alert('Intake complete!')}
      onQuestion={(blockId, questionId, text) => {
        console.log(`Question: ${text}`);
      }}
    />
  );
}
```

### `ValidationDialog`

Modal dialog for human-in-the-loop validation (approve/reject with feedback).

```tsx
import { ValidationDialog, ValidationData } from './components/agui';

function ValidationPage() {
  const [validation, setValidation] = useState<ValidationData | null>(null);

  // Triggered by VALIDATION_REQUIRED event
  const handleValidationRequired = (data: ValidationData) => {
    setValidation(data);
  };

  if (!validation) return null;

  return (
    <ValidationDialog
      validation={validation}
      baseUrl="/api"
      onSubmit={(result) => {
        console.log('Submitted:', result);
        setValidation(null);
      }}
      onCancel={() => setValidation(null)}
    />
  );
}
```

## Event Types

```typescript
enum EventType {
  // Lifecycle
  RUN_STARTED = 'RUN_STARTED',
  RUN_FINISHED = 'RUN_FINISHED',
  RUN_ERROR = 'RUN_ERROR',

  // Text streaming
  TEXT_MESSAGE_START = 'TEXT_MESSAGE_START',
  TEXT_MESSAGE_CONTENT = 'TEXT_MESSAGE_CONTENT',
  TEXT_MESSAGE_END = 'TEXT_MESSAGE_END',

  // Tool calls
  TOOL_CALL_START = 'TOOL_CALL_START',
  TOOL_CALL_ARGS = 'TOOL_CALL_ARGS',
  TOOL_CALL_END = 'TOOL_CALL_END',

  // State sync
  STATE_SNAPSHOT = 'STATE_SNAPSHOT',
  STATE_DELTA = 'STATE_DELTA',

  // Workflow steps
  STEP_STARTED = 'STEP_STARTED',
  STEP_FINISHED = 'STEP_FINISHED',

  // EB-1A Custom
  AGENT_HANDOFF = 'AGENT_HANDOFF',
  VALIDATION_REQUIRED = 'VALIDATION_REQUIRED',
  VALIDATION_RESULT = 'VALIDATION_RESULT',
  DOCUMENT_GENERATED = 'DOCUMENT_GENERATED',
  INTAKE_QUESTION = 'INTAKE_QUESTION',
  INTAKE_ANSWER = 'INTAKE_ANSWER',
}
```

## API Endpoints

The components connect to these backend endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agui/run` | POST | Execute workflow with SSE streaming |
| `/agui/agent` | POST | Invoke single agent with streaming |
| `/agui/validation/submit` | POST | Submit validation result |
| `/agui/health` | GET | Health check |
| `/agui/ws/{case_id}` | WS | WebSocket bi-directional |

## Installation

These components require React 18+ and are written in TypeScript.

```bash
# No additional dependencies needed if you have React
npm install react react-dom
```

## Backend Integration

Ensure your FastAPI backend includes the AG-UI router:

```python
from core.agui.middleware import include_agui_router

app = FastAPI()
include_agui_router(app)
```

## Styling

Components use inline styles by default. Override with CSS classes:

```tsx
<IntakeProgress
  className="my-custom-progress"
  // ...
/>
```

```css
.my-custom-progress {
  /* Your custom styles */
}
```

## Files

| File | Description |
|------|-------------|
| `types.ts` | TypeScript type definitions |
| `useAGUIStream.ts` | SSE streaming hook |
| `IntakeProgress.tsx` | Progress display component |
| `ValidationDialog.tsx` | HITL validation dialog |
| `index.ts` | Module exports |
