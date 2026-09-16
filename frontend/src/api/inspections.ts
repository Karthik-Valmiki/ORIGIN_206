import { apiClient } from './client'

export type InspectionStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLIANT'
  | 'NON_COMPLIANT'
  | 'REVIEW_REQUIRED'
  | 'PROCESSING_FAILED'

export interface InspectionImage {
  id: string
  file_path: string
  ocr_status: string
}

export interface Finding {
  id: string
  finding_type: string
  status: string
  details?: {
    clause_id?: string
    field_name?: string
    observed_value?: string
    required_value?: string
    reason?: string
    evidence?: {
      image_id?: string
      confidence?: number
      bounding_box?: [number, number, number, number] | null
    }
  }
}

export interface Inspection {
  id: string
  inspection_number: string
  status: InspectionStatus
  product_name?: string
  location?: string
  is_imported: boolean
  notes?: string
  created_at: string
  updated_at: string
  product_category_id: string
  rule_id: string
  officer_id: string
  category_name?: string
  officer_name?: string
  images?: InspectionImage[]
  findings?: Finding[]
  verdict_summary?: string
  error_message?: string
}

export interface InspectionListResponse {
  data: Inspection[]
  total: number
}

export interface CreateInspectionPayload {
  category_id: string
  product_name?: string
  location?: string
  is_imported?: boolean
  notes?: string
  images: File[]
}

export async function createInspection(payload: CreateInspectionPayload): Promise<Inspection> {
  const form = new FormData()
  form.append('category_id', payload.category_id)
  if (payload.product_name) form.append('product_name', payload.product_name)
  if (payload.location) form.append('location', payload.location)
  form.append('is_imported', String(payload.is_imported ?? false))
  if (payload.notes) form.append('notes', payload.notes)
  payload.images.forEach((img) => form.append('images', img))

  const { data } = await apiClient.post<Inspection>('/inspections/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listInspections(skip = 0, limit = 50): Promise<InspectionListResponse> {
  const { data } = await apiClient.get<InspectionListResponse>('/inspections/', {
    params: { skip, limit },
  })
  return data
}

export async function getInspection(id: string): Promise<Inspection> {
  const { data } = await apiClient.get<Inspection>(`/inspections/${id}`)
  return data
}

export async function retryInspection(id: string, images: File[]): Promise<void> {
  const form = new FormData()
  images.forEach((img) => form.append('images', img))
  await apiClient.post(`/inspections/${id}/retry`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
