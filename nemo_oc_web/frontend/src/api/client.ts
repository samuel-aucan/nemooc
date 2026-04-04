import axios from 'axios'

export class ApiError extends Error {
  status?: number
}

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  paramsSerializer: (params) => {
    const parts: string[] = []
    for (const [key, value] of Object.entries(params)) {
      if (value == null || value === '' || value === undefined) continue
      if (Array.isArray(value)) {
        for (const v of value) {
          if (v != null && v !== '') parts.push(`${key}=${encodeURIComponent(v)}`)
        }
      } else {
        parts.push(`${key}=${encodeURIComponent(value as string)}`)
      }
    }
    return parts.join('&')
  },
})

api.interceptors.response.use(
  r => r,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Error desconocido'
    const apiError = new ApiError(msg)
    apiError.status = err.response?.status
    return Promise.reject(apiError)
  }
)

export default api
