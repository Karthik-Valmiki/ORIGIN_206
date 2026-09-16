import { apiClient } from './client'

export interface User {
  id: string
  full_name: string
  email: string
  is_active: boolean
  roles: string[]
  created_at: string
}

export interface UserListResponse {
  data: User[]
  total: number
}

export interface CreateUserPayload {
  full_name: string
  email: string
  password: string
  roles: string[]
}

export async function listUsers(skip = 0, limit = 100): Promise<User[]> {
  const { data } = await apiClient.get<User[]>('/admin/users', {
    params: { skip, limit },
  })
  return data
}

export async function createUser(payload: CreateUserPayload): Promise<User> {
  const { data } = await apiClient.post<User>('/admin/users', payload)
  return data
}

export async function deactivateUser(id: string): Promise<void> {
  await apiClient.patch(`/admin/users/${id}/deactivate`)
}

export async function activateUser(id: string): Promise<void> {
  await apiClient.patch(`/admin/users/${id}/activate`)
}
