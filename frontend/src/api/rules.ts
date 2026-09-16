import { apiClient } from './client'

export interface Rule {
  id: string
  name: string
  category_id?: string
  category_name?: string
  version: number
  status: 'DRAFT' | 'VALIDATED' | 'PUBLISHED'
  effective_from?: string
  created_at: string
  rule_data: Record<string, unknown>
}

export interface RuleListResponse {
  data: Rule[]
  total: number
}

export async function listRules(): Promise<RuleListResponse> {
  const { data } = await apiClient.get<RuleListResponse>('/admin/rules')
  return data
}

export async function getRule(id: string): Promise<Rule> {
  const { data } = await apiClient.get<Rule>(`/admin/rules/${id}`)
  return data
}

export async function createRule(payload: Partial<Rule>): Promise<Rule> {
  const { data } = await apiClient.post<Rule>('/admin/rules', payload)
  return data
}

export async function validateRule(payload: Partial<Rule>): Promise<{ valid: boolean; errors?: string[] }> {
  const { data } = await apiClient.post('/admin/rules/validate', payload)
  return data
}

export async function publishRule(id: string): Promise<Rule> {
  const { data } = await apiClient.post<Rule>(`/admin/rules/${id}/publish`)
  return data
}
