import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    // 处理网络错误（后端未运行、网络断开等）
    if (!error.response) {
      // 判断是否为网络错误
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error' || error.message?.includes('Network')) {
        // 返回统一的网络错误格式
        return Promise.reject({
          success: false,
          message: '网络连接失败，请检查后端服务是否运行',
          code: 500
        })
      }
      // 其他错误（如超时）
      return Promise.reject({
        success: false,
        message: error.message || '请求失败，请稍后再试',
        code: 500
      })
    }
    // 后端返回的错误
    if (error.response.data) {
      return Promise.reject(error.response.data)
    }
    // HTTP 状态码错误
    return Promise.reject({
      success: false,
      message: `请求失败 (${error.response.status})`,
      code: error.response.status
    })
  }
)

const api = {
  auth: {
    checkLogin: () => apiClient.get('/auth/check'),
    login: (username, password) => apiClient.post('/auth/login', { username, password }),
    logout: () => apiClient.post('/auth/logout')
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
    getQrcode: (accountId) => apiClient.get(`/login/qrcode?account_id=${accountId}`)
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
  // 添加通用方法，支持直接调用
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  delete: (url, config) => apiClient.delete(url, config)
}

export default api
export { apiClient }

