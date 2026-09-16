import { apiClient } from './client'

export interface AuditEntry {
  id: string
  user_id?: string
  action: string
  entity_name: string
  entity_id?: string
  created_at: string
  payload?: Record<string, unknown>
}

export interface AuditListResponse {
  data: AuditEntry[]
  total: number
}

export async function listAuditLog(skip = 0, limit = 100): Promise<AuditListResponse> {
  const { data } = await apiClient.get<AuditListResponse>('/admin/audit-logs', {
    params: { skip, limit },
  })
  return data
}
