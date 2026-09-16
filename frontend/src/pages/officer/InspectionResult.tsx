import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, Download } from 'lucide-react'
import { getInspection } from '../../api/inspections'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { FindingRow } from '../../components/inspection/FindingRow'
import { EvidenceViewer } from '../../components/inspection/EvidenceViewer'
import { ReviewWorkflow } from './ReviewWorkflow'
import { SkeletonList } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/EmptyState'
import styles from './InspectionResult.module.css'

const STATUS_SUMMARY: Record<string, string> = {
  COMPLIANT:         'All statutory declarations verified.',
  NON_COMPLIANT:     'One or more mandatory declarations are non-compliant.',
  REVIEW_REQUIRED:   'Some declarations could not be confidently verified.',
  PROCESSING_FAILED: 'Processing encountered an error.',
}

export function InspectionResult() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [highlightedFinding, setHighlightedFinding] = useState<string | null>(null)

  const { data: inspection, isLoading, isError, refetch } = useQuery({
    queryKey: ['inspection', id],
    queryFn: () => getInspection(id!),
    enabled: !!id,
  })

  if (isLoading) return <div className={styles.page}><SkeletonList count={5} /></div>
  if (isError || !inspection) return (
    <div className={styles.page}>
      <ErrorState message="Could not load this inspection." onRetry={() => refetch()} />
    </div>
  )

  const findings = inspection.findings ?? []
  const images = inspection.images ?? []
  const isFailed = inspection.status === 'PROCESSING_FAILED'
  const needsReview = inspection.status === 'REVIEW_REQUIRED'

  return (
    <div className={styles.page}>
      {/* Back */}
      <button className={styles.back} onClick={() => navigate(-1)} aria-label="Go back">
        <ChevronLeft size={20} />
        Back
      </button>

      {/* ── Summary header ── */}
      <section className={styles.summaryBlock}>
        <p className={styles.inspectionId}>{inspection.inspection_number}</p>
        <p className={styles.product}>{inspection.product_name ?? inspection.category_name ?? 'Product'}</p>

        {/* Verdict — most prominent element */}
        <div className={styles.verdictRow}>
          <StatusBadge status={inspection.status} size="lg" />
        </div>

        <p className={styles.verdictSummary}>
          {inspection.verdict_summary ?? STATUS_SUMMARY[inspection.status] ?? ''}
        </p>

        {isFailed && inspection.error_message && (
          <p className={styles.errorMsg}>{inspection.error_message}</p>
        )}

        <p className={styles.meta}>
          {new Date(inspection.created_at).toLocaleString('en-IN')}
          {inspection.location ? ` · ${inspection.location}` : ''}
        </p>
      </section>

      {/* ── Main body: desktop = side-by-side, mobile = stacked ── */}
      <div className={styles.body}>
        {/* Evidence column */}
        {images.length > 0 && (
          <section className={styles.evidenceCol}>
            <h2 className={styles.sectionTitle}>Evidence</h2>
            <EvidenceViewer
              images={images}
              findings={findings}
              highlightedFinding={highlightedFinding}
              onRegionClick={(clauseId) => setHighlightedFinding(clauseId)}
            />
          </section>
        )}

        {/* Findings column */}
        {findings.length > 0 && (
          <section className={styles.findingsCol}>
            <h2 className={styles.sectionTitle}>Compliance findings</h2>
            <div className={styles.findingsList}>
              {findings.map((f) => (
                <FindingRow
                  key={f.details?.clause_id || f.id}
                  finding={f}
                  isHighlighted={highlightedFinding === f.details?.clause_id}
                  onSelect={() => setHighlightedFinding(
                    highlightedFinding === f.details?.clause_id ? null : (f.details?.clause_id || null)
                  )}
                />
              ))}
            </div>
          </section>
        )}
      </div>

      {/* ── Review workflow (REVIEW_REQUIRED) ── */}
      {needsReview && <ReviewWorkflow inspection={inspection} />}

      {/* ── Actions ── */}
      <section className={styles.actions}>
        <a
          href={`/api/v1/reports/${id}`}
          download
          className={styles.downloadLink}
          aria-label="Download report"
        >
          <Download size={16} aria-hidden="true" />
          Download report
        </a>
      </section>
    </div>
  )
}
