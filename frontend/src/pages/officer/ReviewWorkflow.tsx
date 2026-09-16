import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Inspection } from '../../api/inspections'
import { retryInspection } from '../../api/inspections'
import { submitReview, type ReviewSubmitPayload } from '../../api/reviews'
import { Button } from '../../components/ui/Button'
import { Textarea } from '../../components/ui/Input'
import { ImageUploadGrid } from '../../components/inspection/ImageUploadGrid'
import { useToast } from '../../components/ui/Toast'
import styles from './ReviewWorkflow.module.css'

interface ReviewWorkflowProps {
  inspection: Inspection
}

type Action = 'confirm_compliant' | 'confirm_non_compliant' | 'request_reinspection' | null

export function ReviewWorkflow({ inspection }: ReviewWorkflowProps) {
  const [action, setAction] = useState<Action>(null)
  const [justification, setJustification] = useState('')
  const [reuploadImages, setReuploadImages] = useState<File[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  const reviewMutation = useMutation({
    mutationFn: (payload: ReviewSubmitPayload) => submitReview(inspection.id, payload),
    onSuccess: () => {
      success('Review submitted successfully.')
      queryClient.invalidateQueries({ queryKey: ['inspection', inspection.id] })
      setAction(null)
    },
    onError: () => toastError('Could not submit review. Please try again.'),
  })

  const retryMutation = useMutation({
    mutationFn: (images: File[]) => retryInspection(inspection.id, images),
    onSuccess: () => {
      success('Re-inspection submitted.')
      queryClient.invalidateQueries({ queryKey: ['inspection', inspection.id] })
      setAction(null)
    },
    onError: () => toastError('Could not submit re-inspection. Please try again.'),
  })

  function validate(): boolean {
    const errs: Record<string, string> = {}
    if (!justification.trim()) errs.justification = 'Justification is required before submitting.'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  function handleReviewSubmit(e: FormEvent) {
    e.preventDefault()
    if (!validate() || !action) return

    const MAP: Record<NonNullable<Action>, ReviewSubmitPayload['action']> = {
      confirm_compliant:     'ACCEPT',
      confirm_non_compliant: 'OVERRIDE',
      request_reinspection:  'REQUEST_REINSPECTION',
    }

    if (action === 'request_reinspection') {
      if (reuploadImages.length === 0) {
        setErrors((e) => ({ ...e, images: 'Add at least one image for re-inspection.' }))
        return
      }
      retryMutation.mutate(reuploadImages)
    } else {
      reviewMutation.mutate({ action: MAP[action], comments: justification })
    }
  }

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>Review required</h2>
      <p className={styles.desc}>
        The system could not confidently determine all declarations.
        Choose an action below.
      </p>

      {/* Primary action */}
      <div className={styles.actions}>
        <Button
          variant={action === 'confirm_compliant' ? 'primary' : 'secondary'}
          size="md"
          onClick={() => setAction('confirm_compliant')}
          id="btn-confirm-compliant"
        >
          Confirm compliant
        </Button>

        <Button
          variant={action === 'confirm_non_compliant' ? 'danger' : 'secondary'}
          size="md"
          onClick={() => setAction('confirm_non_compliant')}
          id="btn-confirm-non-compliant"
        >
          Confirm non-compliant
        </Button>

        <Button
          variant={action === 'request_reinspection' ? 'secondary' : 'ghost'}
          size="md"
          onClick={() => setAction('request_reinspection')}
          id="btn-request-reinspection"
        >
          Re-upload images
        </Button>
      </div>

      {/* Justification form */}
      {action && action !== 'request_reinspection' && (
        <form onSubmit={handleReviewSubmit} className={styles.form} noValidate>
          <Textarea
            label="Justification"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Briefly explain your decision…"
            error={errors.justification}
            required
            id="review-justification"
          />
          <Button
            type="submit"
            fullWidth
            loading={reviewMutation.isPending}
            variant={action === 'confirm_compliant' ? 'primary' : 'danger'}
            id="btn-submit-review"
          >
            Submit decision
          </Button>
        </form>
      )}

      {/* Re-upload form */}
      {action === 'request_reinspection' && (
        <form onSubmit={handleReviewSubmit} className={styles.form} noValidate>
          <p className={styles.reuploadHint}>
            Upload clearer images. Previous images are retained.
          </p>
          <ImageUploadGrid onChange={setReuploadImages} error={errors.images} />
          <Textarea
            label="Reason for re-upload (required)"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="e.g. MRP panel was obscured in original images"
            error={errors.justification}
            required
            id="reupload-justification"
          />
          <Button
            type="submit"
            fullWidth
            loading={retryMutation.isPending}
            id="btn-submit-reupload"
          >
            Submit for re-processing
          </Button>
        </form>
      )}
    </section>
  )
}
