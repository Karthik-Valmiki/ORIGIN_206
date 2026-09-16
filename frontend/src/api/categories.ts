import { apiClient } from './client'

export interface Category {
  id: string
  category_name: string
  description?: string
}

export async function listCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>('/categories/')
  return data
}
