/**
 * IntakeProgress - Real-time intake questionnaire progress component
 *
 * Displays progress through the EB-1A intake questionnaire blocks.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useAGUIStream } from './useAGUIStream';
import { AGUIEvent, EventType, IntakeBlock, IntakeProgressData } from './types';

export interface IntakeProgressProps {
  /** Case ID for the intake */
  caseId: string;
  /** API base URL */
  baseUrl?: string;
  /** Callback when intake completes */
  onComplete?: () => void;
  /** Callback when a question is shown */
  onQuestion?: (blockId: string, questionId: string, text: string) => void;
  /** Callback when validation is required */
  onValidationRequired?: (data: Record<string, unknown>) => void;
  /** Additional CSS class */
  className?: string;
}

// 13 intake blocks definition
const INTAKE_BLOCKS: IntakeBlock[] = [
  { id: 'basic_info', title: 'Basic Information', description: 'Personal details', questionsCount: 8 },
  { id: 'family_childhood', title: 'Family & Childhood', description: 'Family background', questionsCount: 4 },
  { id: 'school', title: 'School', description: 'Education history', questionsCount: 9 },
  { id: 'university', title: 'University', description: 'Higher education', questionsCount: 10 },
  { id: 'career', title: 'Career', description: 'Professional experience', questionsCount: 5 },
  { id: 'projects_research', title: 'Projects & Research', description: 'Original contributions', questionsCount: 12 },
  { id: 'awards', title: 'Awards', description: 'Recognition & honors', questionsCount: 7 },
  { id: 'talks_public_activity', title: 'Public Activity', description: 'Conferences & media', questionsCount: 10 },
  { id: 'courses_certificates', title: 'Certifications', description: 'Professional development', questionsCount: 2 },
  { id: 'compensation', title: 'Compensation', description: 'Salary information', questionsCount: 7 },
  { id: 'recommenders', title: 'Recommenders', description: 'Reference contacts', questionsCount: 5 },
  { id: 'goals_usa', title: 'Goals in USA', description: 'Future plans', questionsCount: 3 },
  { id: 'final_merits', title: 'Final Merits', description: 'Sustained acclaim', questionsCount: 7 },
];

export function IntakeProgress({
  caseId,
  baseUrl = '',
  onComplete,
  onQuestion,
  onValidationRequired,
  className = '',
}: IntakeProgressProps): JSX.Element {
  const [progress, setProgress] = useState<IntakeProgressData>({
    caseId,
    currentBlock: '',
    currentStep: 0,
    completedBlocks: [],
    totalBlocks: INTAKE_BLOCKS.length,
    percentage: 0,
  });

  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [isComplete, setIsComplete] = useState(false);

  const handleEvent = (event: AGUIEvent) => {
    switch (event.type) {
      case EventType.INTAKE_QUESTION:
        if (event.metadata) {
          const blockId = event.metadata.block_id as string;
          const questionId = event.metadata.question_id as string;
          const questionText = event.metadata.question_text as string;

          setCurrentQuestion(questionText || '');
          setProgress((prev) => ({
            ...prev,
            currentBlock: blockId,
          }));

          onQuestion?.(blockId, questionId, questionText);
        }
        break;

      case EventType.STEP_FINISHED:
        if (event.step_name) {
          setProgress((prev) => {
            const newCompletedBlocks = prev.completedBlocks.includes(event.step_name!)
              ? prev.completedBlocks
              : [...prev.completedBlocks, event.step_name!];

            return {
              ...prev,
              completedBlocks: newCompletedBlocks,
              percentage: Math.round((newCompletedBlocks.length / prev.totalBlocks) * 100),
            };
          });
        }
        break;

      case EventType.VALIDATION_REQUIRED:
        if (event.metadata) {
          onValidationRequired?.(event.metadata);
        }
        break;

      case EventType.RUN_FINISHED:
        setIsComplete(true);
        onComplete?.();
        break;
    }
  };

  const { isConnected, isLoading, error, startWorkflow } = useAGUIStream({
    baseUrl,
    onEvent: handleEvent,
  });

  // Start workflow when component mounts
  useEffect(() => {
    startWorkflow({
      case_id: caseId,
      operation: 'intake_questionnaire',
    });
  }, [caseId, startWorkflow]);

  const currentBlockInfo = useMemo(() => {
    return INTAKE_BLOCKS.find((b) => b.id === progress.currentBlock);
  }, [progress.currentBlock]);

  const blockIndex = useMemo(() => {
    return INTAKE_BLOCKS.findIndex((b) => b.id === progress.currentBlock);
  }, [progress.currentBlock]);

  return (
    <div className={`agui-intake-progress ${className}`} style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>EB-1A Intake Questionnaire</h2>
        <span style={styles.caseId}>Case: {caseId}</span>
      </div>

      {/* Progress bar */}
      <div style={styles.progressBarContainer}>
        <div
          style={{
            ...styles.progressBar,
            width: `${progress.percentage}%`,
          }}
        />
        <span style={styles.progressText}>{progress.percentage}% Complete</span>
      </div>

      {/* Status */}
      <div style={styles.statusRow}>
        <span
          style={{
            ...styles.statusDot,
            backgroundColor: isConnected ? '#22c55e' : isLoading ? '#f59e0b' : '#ef4444',
          }}
        />
        <span style={styles.statusText}>
          {isComplete
            ? 'Completed'
            : isLoading
            ? 'Processing...'
            : isConnected
            ? 'Connected'
            : 'Disconnected'}
        </span>
      </div>

      {/* Error display */}
      {error && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {error.message}
        </div>
      )}

      {/* Current block info */}
      {currentBlockInfo && !isComplete && (
        <div style={styles.currentBlock}>
          <div style={styles.blockHeader}>
            <span style={styles.blockNumber}>
              Block {blockIndex + 1} of {INTAKE_BLOCKS.length}
            </span>
            <h3 style={styles.blockTitle}>{currentBlockInfo.title}</h3>
            <p style={styles.blockDescription}>{currentBlockInfo.description}</p>
          </div>

          {currentQuestion && (
            <div style={styles.questionBox}>
              <p style={styles.questionText}>{currentQuestion}</p>
            </div>
          )}
        </div>
      )}

      {/* Completion message */}
      {isComplete && (
        <div style={styles.completeBox}>
          <span style={styles.completeIcon}>✓</span>
          <h3 style={styles.completeTitle}>Intake Complete!</h3>
          <p style={styles.completeText}>
            All {INTAKE_BLOCKS.length} sections have been completed.
          </p>
        </div>
      )}

      {/* Block list */}
      <div style={styles.blockList}>
        {INTAKE_BLOCKS.map((block, index) => {
          const isCompleted = progress.completedBlocks.includes(block.id);
          const isCurrent = block.id === progress.currentBlock;

          return (
            <div
              key={block.id}
              style={{
                ...styles.blockItem,
                ...(isCompleted ? styles.blockCompleted : {}),
                ...(isCurrent ? styles.blockCurrent : {}),
              }}
            >
              <span style={styles.blockIndex}>{index + 1}</span>
              <span style={styles.blockName}>{block.title}</span>
              {isCompleted && <span style={styles.checkmark}>✓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Inline styles (can be overridden via className)
const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: '600px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    paddingBottom: '15px',
    borderBottom: '1px solid #e5e7eb',
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: '#111827',
  },
  caseId: {
    fontSize: '12px',
    color: '#6b7280',
    fontFamily: 'monospace',
  },
  progressBarContainer: {
    position: 'relative',
    height: '24px',
    backgroundColor: '#e5e7eb',
    borderRadius: '12px',
    overflow: 'hidden',
    marginBottom: '15px',
  },
  progressBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    height: '100%',
    backgroundColor: '#3b82f6',
    transition: 'width 0.3s ease',
    borderRadius: '12px',
  },
  progressText: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    fontSize: '12px',
    fontWeight: 500,
    color: '#374151',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '20px',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  statusText: {
    fontSize: '14px',
    color: '#6b7280',
  },
  errorBox: {
    padding: '12px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    color: '#dc2626',
    fontSize: '14px',
    marginBottom: '15px',
  },
  currentBlock: {
    padding: '20px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  blockHeader: {
    marginBottom: '15px',
  },
  blockNumber: {
    fontSize: '12px',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  blockTitle: {
    margin: '5px 0',
    fontSize: '18px',
    fontWeight: 600,
    color: '#111827',
  },
  blockDescription: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280',
  },
  questionBox: {
    padding: '15px',
    backgroundColor: '#fff',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
  },
  questionText: {
    margin: 0,
    fontSize: '15px',
    color: '#374151',
    lineHeight: 1.5,
  },
  completeBox: {
    textAlign: 'center',
    padding: '30px',
    backgroundColor: '#f0fdf4',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  completeIcon: {
    display: 'inline-block',
    width: '48px',
    height: '48px',
    lineHeight: '48px',
    fontSize: '24px',
    backgroundColor: '#22c55e',
    color: '#fff',
    borderRadius: '50%',
    marginBottom: '15px',
  },
  completeTitle: {
    margin: '0 0 10px',
    fontSize: '18px',
    fontWeight: 600,
    color: '#166534',
  },
  completeText: {
    margin: 0,
    fontSize: '14px',
    color: '#166534',
  },
  blockList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  blockItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 12px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    fontSize: '14px',
    color: '#6b7280',
  },
  blockCompleted: {
    backgroundColor: '#f0fdf4',
    color: '#166534',
  },
  blockCurrent: {
    backgroundColor: '#eff6ff',
    color: '#1d4ed8',
    fontWeight: 500,
  },
  blockIndex: {
    width: '24px',
    height: '24px',
    lineHeight: '24px',
    textAlign: 'center',
    backgroundColor: '#e5e7eb',
    borderRadius: '50%',
    fontSize: '12px',
    fontWeight: 500,
  },
  blockName: {
    flex: 1,
  },
  checkmark: {
    color: '#22c55e',
    fontWeight: 'bold',
  },
};

export default IntakeProgress;
