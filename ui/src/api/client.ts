import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api'

// Debug: Log the API base URL being used (always log for debugging)
console.log('🔍 API Base URL:', baseURL)
console.log('🔍 VITE_API_BASE env var:', import.meta.env.VITE_API_BASE || 'NOT SET')
console.log('🔍 Environment mode:', import.meta.env.MODE)

export const apiClient = axios.create({
  baseURL,
  withCredentials: false,
  timeout: 30000, // 30 second timeout
})

// Add request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    const fullUrl = `${config.baseURL || ''}${config.url || ''}`
    console.log('📤 API Request:', config.method?.toUpperCase(), fullUrl)
    return config
  },
  (error) => {
    console.error('❌ API Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('❌ API Error Response:', {
        status: error.response.status,
        statusText: error.response.statusText,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        data: error.response.data,
      })
    } else if (error.request) {
      // Request made but no response received
      console.error('❌ API Network Error:', {
        message: error.message,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      })
    } else {
      // Something else happened
      console.error('❌ API Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export function setAuthToken(token: string | null) {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete apiClient.defaults.headers.common.Authorization
  }
}
