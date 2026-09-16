import type { InspectionStatus } from '../../api/inspections'
import styles from './StatusBadge.module.css'

interface StatusBadgeProps {
  status: InspectionStatus | string
  size?: 'sm' | 'md' | 'lg'
}

const STATUS_MAP: Record<string, { label: string; icon: string; cls: string }> = {
  COMPLIANT:        { label: 'Compliant',        icon: '✓', cls: 'compliant' },
  NON_COMPLIANT:    { label: 'Non-compliant',     icon: '✕', cls: 'violation' },
  REVIEW_REQUIRED:  { label: 'Review required',   icon: '!', cls: 'review' },
  PROCESSING_FAILED:{ label: 'Processing failed', icon: '⚠', cls: 'failed' },
  PENDING:          { label: 'Processing',        icon: '○', cls: 'neutral' },
  PROCESSING:       { label: 'Processing',        icon: '●', cls: 'neutral' },
  // Finding-level
  PASSED:           { label: 'Passed',            icon: '✓', cls: 'compliant' },
  FAILED:           { label: 'Violation',         icon: '✕', cls: 'violation' },
  SKIPPED:          { label: 'Skipped',           icon: '–', cls: 'neutral' },
  DRAFT:            { label: 'Draft',             icon: '○', cls: 'neutral' },
  VALIDATED:        { label: 'Validated',         icon: '✓', cls: 'info' },
  PUBLISHED:        { label: 'Published',         icon: '●', cls: 'compliant' },
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? { label: status, icon: '?', cls: 'neutral' }

  return (
    <span
      className={[styles.badge, styles[config.cls], styles[size]].join(' ')}
      role="status"
      aria-label={config.label}
    >
      <span className={styles.icon} aria-hidden="true">{config.icon}</span>
      <span>{config.label}</span>
    </span>
  )
}
