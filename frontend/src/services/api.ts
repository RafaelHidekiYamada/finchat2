import axios, { AxiosError } from 'axios'
import type { ApiError } from '../types'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('finchat_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('finchat_token')
      window.dispatchEvent(new Event('finchat:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiError>(error)) return error.response?.data?.error?.message || 'Não foi possível concluir a operação.'
  return 'Ocorreu um erro inesperado.'
}
