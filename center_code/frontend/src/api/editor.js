import { apiClient } from './index'

/**
 * 视频剪辑 API
 */
export const editVideo = (data) => {
  return apiClient.post('/editor/edit', data)
}

export const editVideoAsync = (data) => {
  return apiClient.post('/editor/edit_async', data)
}

export const getTasks = (params) => {
  return apiClient.get('/tasks', { params })
}

export const getTask = (taskId) => {
  return apiClient.get(`/tasks/${taskId}`)
}

export const deleteTask = (taskId, deleteOutput = false) => {
  return apiClient.post(`/tasks/${taskId}/delete`, { delete_output: deleteOutput })
}

