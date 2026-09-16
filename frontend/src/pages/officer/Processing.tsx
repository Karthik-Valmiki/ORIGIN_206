import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getInspection, type InspectionStatus } from '../../api/inspections'
import styles from './Processing.module.css'

const TERMINAL: InspectionStatus[] = ['COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED']

type PipelineStep = {
  key: string
  label: string
  states: InspectionStatus[]
}

// Map backend states to pipeline steps.
// Step is "done" once we've passed it, "active" when it applies.
const PIPELINE: PipelineStep[] = [
  { key: 'upload',   label: 'Images uploaded',        states: ['PENDING', 'PROCESSING', 'COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'] },
  { key: 'preproc',  label: 'Image quality checked',  states: ['PROCESSING', 'COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'] },
  { key: 'ocr',      label: 'Reading label text',     states: ['PROCESSING', 'COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'] },
  { key: 'rules',    label: 'Checking declarations',  states: ['COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'] },
  { key: 'result',   label: 'Preparing result',       states: ['COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', 'PROCESSING_FAILED'] },
]

function stepState(step: PipelineStep, status: InspectionStatus, stepIdx: number, allSteps: PipelineStep[]): 'done' | 'active' | 'pending' | 'failed' {
  if (status === 'PROCESSING_FAILED') return stepIdx === allSteps.length - 1 ? 'failed' : 'done'
  if (step.states.includes(status)) {
    // If next step also applies → this one is done
    const next = allSteps[stepIdx + 1]
    if (!next || next.states.includes(status)) return 'done'
    return 'active'
  }
  return 'pending'
}

export function Processing() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: inspection } = useQuery({
    queryKey: ['inspection', id],
    queryFn: () => getInspection(id!),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL.includes(status)) return false
      return 2500
    },
    enabled: !!id,
  })

  // Navigate when terminal status reached
  useEffect(() => {
    if (!inspection) return
    if (inspection.status === 'PROCESSING_FAILED') return // stay, show failed state
    if (TERMINAL.includes(inspection.status)) {
      navigate(`/officer/inspect/${id}/result`, { replace: true })
    }
  }, [inspection, id, navigate])

  const status = inspection?.status ?? 'PENDING'
  const isFailed = status === 'PROCESSING_FAILED'

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <p className={styles.inspectionId}>
          Inspection {inspection?.inspection_number ?? '…'}
        </p>

        {isFailed ? (
          <div className={styles.failedBlock}>
            <p className={styles.failedTitle}>⚠ Processing failed</p>
            <p className={styles.failedDesc}>
              {inspection?.error_message ?? 'An error occurred during processing.'}
            </p>
            <button
              className={styles.retryLink}
              onClick={() => navigate(`/officer/inspect/${id}/result`)}
            >
              View details and re-upload
            </button>
          </div>
        ) : (
          <>
            <h1 className={styles.heading}>Processing product label</h1>
            <div className={styles.pipeline} role="list" aria-label="Processing steps">
              {PIPELINE.map((step, idx) => {
                const s = stepState(step, status as InspectionStatus, idx, PIPELINE)
                return (
                  <div
                    key={step.key}
                    className={[styles.step, styles[s]].join(' ')}
                    role="listitem"
                    aria-current={s === 'active' ? 'step' : undefined}
                  >
                    <span className={styles.stepDot} aria-hidden="true">
                      {s === 'done' ? '✓' : s === 'active' ? '●' : '○'}
                    </span>
                    <span className={styles.stepLabel}>{step.label}</span>
                  </div>
                )
              })}
            </div>
            <p className={styles.hint}>This usually takes a few moments.</p>
          </>
        )}
      </div>
    </div>
  )
}
