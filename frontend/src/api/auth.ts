import { apiClient } from './client'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface MeResponse {
  id: string
  full_name: string
  email: string
  roles: string[]
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  const { data } = await apiClient.post<LoginResponse>('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function getMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>('/auth/me')
  return data
}
