import { apiClient } from './client'

export interface ReviewSubmitPayload {
  action: 'ACCEPT' | 'OVERRIDE' | 'REQUEST_REINSPECTION'
  comments: string
}

export async function submitReview(inspectionId: string, payload: ReviewSubmitPayload): Promise<void> {
  await apiClient.post(`/reviews/${inspectionId}/submit`, payload)
}
