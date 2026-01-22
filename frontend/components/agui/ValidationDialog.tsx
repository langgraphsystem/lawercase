/**
 * ValidationDialog - Human-in-the-loop validation modal
 *
 * Displays content for human review with approve/reject options.
 */

import React, { useState } from 'react';
import { AGUIValidationRequest, ValidationData } from './types';

export interface ValidationDialogProps {
  /** Validation data to display */
  validation: ValidationData;
  /** API base URL */
  baseUrl?: string;
  /** Callback when validation is submitted */
  onSubmit?: (result: AGUIValidationRequest) => void;
  /** Callback when dialog is cancelled */
  onCancel?: () => void;
  /** Additional CSS class */
  className?: string;
}

export function ValidationDialog({
  validation,
  baseUrl = '',
  onSubmit,
  onCancel,
  className = '',
}: ValidationDialogProps): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (approved: boolean) => {
    setIsSubmitting(true);
    setError(null);

    const request: AGUIValidationRequest = {
      validation_id: validation.validationId,
      approved,
      feedback: feedback.trim() || undefined,
    };

    try {
      const response = await fetch(`${baseUrl}/agui/validation/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      onSubmit?.(request);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to submit validation';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`agui-validation-overlay ${className}`} style={styles.overlay}>
      <div style={styles.dialog}>
        {/* Header */}
        <div style={styles.header}>
          <h2 style={styles.title}>{validation.title || 'Review Required'}</h2>
          <button
            onClick={onCancel}
            style={styles.closeButton}
            disabled={isSubmitting}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {/* Validation type badge */}
          <span style={styles.typeBadge}>{validation.validationType}</span>

          {/* Description */}
          {validation.description && (
            <p style={styles.description}>{validation.description}</p>
          )}

          {/* Data preview */}
          <div style={styles.dataPreview}>
            <h4 style={styles.dataTitle}>Content to Review:</h4>
            <pre style={styles.dataContent}>
              {typeof validation.data === 'string'
                ? validation.data
                : JSON.stringify(validation.data, null, 2)}
            </pre>
          </div>

          {/* Feedback input */}
          <div style={styles.feedbackSection}>
            <label style={styles.feedbackLabel} htmlFor="validation-feedback">
              Feedback (optional):
            </label>
            <textarea
              id="validation-feedback"
              style={styles.feedbackInput}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Add any comments or suggestions..."
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          {/* Error display */}
          {error && <div style={styles.errorBox}>{error}</div>}
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <button
            onClick={() => handleSubmit(false)}
            style={{ ...styles.button, ...styles.rejectButton }}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Reject'}
          </button>
          <button
            onClick={() => handleSubmit(true)}
            style={{ ...styles.button, ...styles.approveButton }}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Approve'}
          </button>
        </div>

        {/* Case ID footer */}
        <div style={styles.footer}>
          <span style={styles.caseId}>Case: {validation.caseId}</span>
          <span style={styles.validationId}>ID: {validation.validationId}</span>
        </div>
      </div>
    </div>
  );
}

// Inline styles
const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  dialog: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.2)',
    maxWidth: '600px',
    width: '100%',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid #e5e7eb',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: '#111827',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    color: '#6b7280',
    cursor: 'pointer',
    padding: '0 5px',
    lineHeight: 1,
  },
  content: {
    padding: '24px',
    overflowY: 'auto',
    flex: 1,
  },
  typeBadge: {
    display: 'inline-block',
    padding: '4px 10px',
    backgroundColor: '#dbeafe',
    color: '#1d4ed8',
    borderRadius: '9999px',
    fontSize: '12px',
    fontWeight: 500,
    textTransform: 'uppercase',
    marginBottom: '16px',
  },
  description: {
    margin: '0 0 20px',
    fontSize: '14px',
    color: '#6b7280',
    lineHeight: 1.5,
  },
  dataPreview: {
    marginBottom: '20px',
  },
  dataTitle: {
    margin: '0 0 10px',
    fontSize: '14px',
    fontWeight: 500,
    color: '#374151',
  },
  dataContent: {
    margin: 0,
    padding: '16px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    fontSize: '13px',
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    maxHeight: '200px',
    overflowY: 'auto',
    color: '#374151',
  },
  feedbackSection: {
    marginBottom: '16px',
  },
  feedbackLabel: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: 500,
    color: '#374151',
  },
  feedbackInput: {
    width: '100%',
    padding: '12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  errorBox: {
    padding: '12px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    color: '#dc2626',
    fontSize: '14px',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 24px',
    borderTop: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
  },
  button: {
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    transition: 'background-color 0.2s',
  },
  rejectButton: {
    backgroundColor: '#fee2e2',
    color: '#dc2626',
  },
  approveButton: {
    backgroundColor: '#22c55e',
    color: '#fff',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '12px 24px',
    backgroundColor: '#f9fafb',
    borderTop: '1px solid #e5e7eb',
    fontSize: '12px',
    color: '#9ca3af',
    fontFamily: 'monospace',
  },
  caseId: {},
  validationId: {},
};

export default ValidationDialog;
