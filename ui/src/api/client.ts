import axios from 'axios'

// Determine base URL based on environment
// IMPORTANT: Vite environment variables are embedded at BUILD TIME
// For Cloudflare Pages, set VITE_API_BASE in the Cloudflare dashboard before building
const getBaseURL = (): string => {
  // Check if we're in development mode
  const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'
  
  // Runtime check: Look for API URL in window config (for runtime override)
  // This allows overriding the build-time value if needed
  if (typeof window !== 'undefined') {
    const runtimeApiBase = (window as any).__API_BASE_URL__
    if (runtimeApiBase && typeof runtimeApiBase === 'string' && runtimeApiBase.trim() !== '') {
      console.log('🔍 Using runtime API base URL from window.__API_BASE_URL__:', runtimeApiBase)
      return runtimeApiBase.trim()
    }
  }
  
  // Build-time env var (embedded during Vite build)
  const envBase = import.meta.env.VITE_API_BASE
  
  // If VITE_API_BASE is explicitly set, use it
  if (envBase && envBase.trim() !== '') {
    return envBase.trim()
  }
  
  // ONLY use localhost in development mode
  if (isDevelopment) {
    return 'http://localhost:8000/api'
  }
  
  // Production mode: NEVER use localhost
  // If VITE_API_BASE is not set, this means the build was done without it
  // For Railway + Cloudflare (different domains), VITE_API_BASE MUST be set in Cloudflare Pages
  console.error('❌ VITE_API_BASE not set in production build!')
  console.error('   Set VITE_API_BASE in Cloudflare Pages → Settings → Environment Variables')
  console.error('   Then rebuild/redeploy the frontend')
  console.error('   Example: VITE_API_BASE=https://your-railway-backend.railway.app/api')
  
  // Fallback: try to detect if we're on a known production domain and construct URL
  // This is a last resort and may not work for all setups
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    // If on Cloudflare Pages, we can't auto-detect Railway URL, so we must fail
    console.error('   Current hostname:', hostname)
    console.error('   Cannot auto-detect backend URL. Please set VITE_API_BASE and rebuild.')
  }
  
  // Return empty string to force explicit error (better than wrong URL)
  // This will cause API calls to fail with clear error messages
  return ''
}

const baseURL = getBaseURL()

// Validate baseURL - prevent empty string in production
if (!baseURL || baseURL.trim() === '') {
  const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'
  if (!isDevelopment) {
    // In production, empty baseURL is a critical error
    const errorMsg = 'CRITICAL: API base URL is not configured. Set VITE_API_BASE in Cloudflare Pages environment variables and rebuild.'
    console.error('❌', errorMsg)
    // Don't throw - let it fail gracefully with network errors that show the issue
  }
}

// Debug: Log the API base URL being used (always log for debugging)
console.log('🔍 API Base URL:', baseURL || '(EMPTY - will cause API calls to fail)')
console.log('🔍 VITE_API_BASE env var:', import.meta.env.VITE_API_BASE || 'NOT SET')
console.log('🔍 Environment mode:', import.meta.env.MODE)
console.log('🔍 Is development:', import.meta.env.DEV)

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
