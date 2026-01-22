/**
 * AG-UI React Components
 *
 * Components for integrating AG-UI protocol with React applications.
 *
 * @example
 * ```tsx
 * import {
 *   useAGUIStream,
 *   IntakeProgress,
 *   ValidationDialog,
 *   EventType,
 * } from './components/agui';
 *
 * function App() {
 *   const { startWorkflow, events, isConnected } = useAGUIStream({
 *     baseUrl: '/api',
 *     onEvent: (event) => console.log('Event:', event),
 *   });
 *
 *   return (
 *     <IntakeProgress
 *       caseId="case-123"
 *       baseUrl="/api"
 *       onComplete={() => console.log('Done!')}
 *     />
 *   );
 * }
 * ```
 */

// Types
export * from './types';

// Hooks
export { useAGUIStream } from './useAGUIStream';
export type { UseAGUIStreamOptions, UseAGUIStreamReturn } from './useAGUIStream';

// Components
export { IntakeProgress } from './IntakeProgress';
export type { IntakeProgressProps } from './IntakeProgress';

export { ValidationDialog } from './ValidationDialog';
export type { ValidationDialogProps } from './ValidationDialog';
