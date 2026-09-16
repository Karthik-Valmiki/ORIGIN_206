import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { Finding } from '../../api/inspections'
import { StatusBadge } from '../ui/StatusBadge'
import styles from './FindingRow.module.css'

interface FindingRowProps {
  finding: Finding
  isHighlighted?: boolean
  onSelect?: () => void
}

const FIELD_LABELS: Record<string, string> = {
  mrp: 'MRP',
  net_quantity: 'Net Quantity',
  manufacturer: 'Manufacturer / Packer',
  consumer_care: 'Consumer Care Contact',
  best_before: 'Best Before / Expiry',
  country_of_origin: 'Country of Origin',
  batch_number: 'Batch / Lot Number',
  importer: 'Importer Details',
}

function humanField(key: string) {
  return FIELD_LABELS[key.toLowerCase()] ?? key.replace(/_/g, ' ')
}

export function FindingRow({ finding, isHighlighted, onSelect }: FindingRowProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={[styles.row, isHighlighted ? styles.highlighted : ''].filter(Boolean).join(' ')}
      onClick={onSelect}
    >
      <button
        type="button"
        className={styles.summary}
        onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v) }}
        aria-expanded={expanded}
        aria-label={`${humanField(finding.details?.field_name || finding.finding_type)} — ${finding.status}`}
      >
        <div className={styles.summaryLeft}>
          <span className={styles.fieldName}>{humanField(finding.details?.field_name || finding.finding_type)}</span>
          {finding.details?.observed_value && (
            <span className={styles.observedValue}>{finding.details?.observed_value}</span>
          )}
        </div>
        <div className={styles.summaryRight}>
          <StatusBadge status={finding.status} size="sm" />
          {expanded ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
        </div>
      </button>

      {expanded && (
        <div className={styles.detail}>
          {finding.details?.observed_value && (
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Observed</span>
              <span className={styles.detailValue}>{finding.details?.observed_value}</span>
            </div>
          )}
          {finding.details?.required_value && (
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Required</span>
              <span className={styles.detailValue}>{finding.details?.required_value}</span>
            </div>
          )}
          {finding.details?.reason && (
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Reason</span>
              <span className={styles.detailValue}>{finding.details?.reason}</span>
            </div>
          )}
          {finding.details?.clause_id && (
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Rule</span>
              <span className={[styles.detailValue, styles.clause].join(' ')}>{finding.details?.clause_id}</span>
            </div>
          )}
          {finding.details?.evidence && (
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Evidence</span>
              <span className={styles.detailValue}>
                {finding.details?.evidence.bounding_box ? 'Image region available' : 'Text extracted'}
                {finding.details?.evidence.confidence != null &&
                  ` · ${finding.details?.evidence.confidence < 0.7 ? 'Low confidence' : 'Confident'}`
                }
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
