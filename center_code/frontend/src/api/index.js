import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

apiClient.interceptors.response.use(
  response => response.data,
  error => {
    if (!error.response) {
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error' || error.message?.includes('Network')) {
        return Promise.reject({
          success: false,
          message: 'Network error, please check the backend service',
          code: 500
        })
      }
      return Promise.reject({
        success: false,
        message: error.message || 'Request failed, please try again',
        code: 500
      })
    }

    if (error.response.status === 401) {
      import('../stores/auth').then(({ useAuthStore }) => {
        const authStore = useAuthStore()
        authStore.isLoggedIn = false
        authStore.username = ''
        authStore.email = ''
        authStore.token = ''
      }).catch(() => {
        console.warn('Unable to import auth store for 401 handling')
      })

      localStorage.removeItem('auth_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      const errorData = error.response.data || {}
      return Promise.reject({
        code: 401,
        message: errorData.message || 'Please log in',
        data: errorData.data || null
      })
    }

    if (error.response.data) {
      return Promise.reject(error.response.data)
    }

    return Promise.reject({
      success: false,
      message: `Request failed (${error.response.status})`,
      code: error.response.status
    })
  }
)

const api = {
  auth: {
    checkLogin: () => apiClient.get('/auth/check'),
    sendCode: (email) => apiClient.post('/auth/send-code', { email }),
    register: (payload) => apiClient.post('/auth/register', payload),
    login: (payload) => apiClient.post('/auth/login', payload),
    logout: () => apiClient.post('/auth/logout'),
    getProfile: () => apiClient.get('/auth/profile'),
    updateProfile: (payload) => apiClient.put('/auth/profile', payload),
    changePassword: (payload) => apiClient.post('/auth/password', payload),
    verifyPassword: (payload) => apiClient.post('/auth/verify-password', payload),
    forgotPassword: (payload) => apiClient.post('/auth/forgot-password', payload),
    resetPassword: (payload) => apiClient.post('/auth/reset-password', payload),
    uploadAvatar: (file) => {
      const form = new FormData()
      form.append('avatar', file)
      return apiClient.post('/auth/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    sendChangeEmailCode: (newEmail) => {
      return apiClient.post('/auth/change-email/send-code', { new_email: newEmail })
    },
    sendOldEmailCode: () => {
      return apiClient.post('/auth/change-email/send-old-code')
    },
    sendNewEmailCode: (newEmail) => {
      return apiClient.post('/auth/change-email/send-new-code', { new_email: newEmail })
    },
    verifyOldEmailCode: (data) => {
      return apiClient.post('/auth/change-email/verify-old-code', { code: data.code })
    },
    verifyChangeEmail: (data) => {
      return apiClient.post('/auth/change-email/verify', {
        new_email: data.newEmail,
        old_code: data.oldEmailCode,
        new_code: data.newEmailCode,
        username: data.username
      })
    },
    updateProfileOnly: (username) => {
      return apiClient.put('/auth/update-profile', { username })
    },
    checkUsernameExists: (username) => {
      return apiClient.post('/auth/check-username', { username })
    },
    checkEmailExists: (email) => {
      return apiClient.post('/auth/check-email', { email })
    }
  },
  stats: {
    get: () => apiClient.get('/stats')
  },
  devices: {
    list: (params) => apiClient.get('/devices', { params }),
    get: (deviceId) => apiClient.get(`/devices/${deviceId}`),
    register: (data) => apiClient.post('/devices/register', data),
    heartbeat: (deviceId) => apiClient.post(`/devices/${deviceId}/heartbeat`)
  },
  accounts: {
    list: (params) => apiClient.get('/accounts', { params }),
    get: (accountId) => apiClient.get(`/accounts/${accountId}`),
    create: (data) => apiClient.post('/accounts', data),
    updateStatus: (accountId, status) => apiClient.put(`/accounts/${accountId}/status`, { status }),
    delete: (accountId) => apiClient.delete(`/accounts/${accountId}`),
    getCookies: (accountId) => apiClient.get(`/accounts/${accountId}/cookies`),
    updateCookies: (accountId, cookies) => apiClient.put(`/accounts/${accountId}/cookies`, { cookies }),
    getCookiesFile: (accountId) => apiClient.get(`/accounts/${accountId}/cookies/file`)
  },
  login: {
    start: (data) => apiClient.post('/login/start', data),
    getQrcode: (accountId) => apiClient.get(`/login/qrcode?account_id=${accountId}`),
    getStatus: (accountId) => apiClient.get(`/login/status?account_id=${accountId}`),
    complete: (data) => apiClient.post('/login/complete', data),
    cancel: (data) => apiClient.post('/login/cancel', data)
  },
  video: {
    upload: (data) => apiClient.post('/video/upload', data),
    tasks: (params) => apiClient.get('/video/tasks', { params }),
    getTask: (taskId) => apiClient.get(`/video/tasks/${taskId}`),
    deleteTask: (taskId) => apiClient.delete(`/video/tasks/${taskId}`)
  },
  chat: {
    send: (data) => apiClient.post('/chat/send', data),
    tasks: (params) => apiClient.get('/chat/tasks', { params }),
    getTask: (taskId) => apiClient.get(`/chat/tasks/${taskId}`)
  },
  listen: {
    tasks: (params) => apiClient.get('/listen/tasks', { params }),
    getTask: (taskId) => apiClient.get(`/listen/tasks/${taskId}`),
    deleteTask: (taskId) => apiClient.delete(`/listen/tasks/${taskId}`)
  },
  social: {
    upload: (data) => apiClient.post('/social/upload', data),
    listen: {
      start: (data) => apiClient.post('/social/listen/start', data),
      stop: (data) => apiClient.post('/social/listen/stop', data),
      messages: (params) => apiClient.get('/social/listen/messages', { params })
    },
    chat: {
      reply: (data) => apiClient.post('/social/chat/reply', data)
    }
  },
  messages: {
    clear: (accountId) => apiClient.post('/messages/clear', { account_id: accountId })
  },
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  delete: (url, config) => apiClient.delete(url, config)
}

export default api
export { apiClient }
