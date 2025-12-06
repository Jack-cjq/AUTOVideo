import { apiClient } from './index'

// 获取项目列表
export const getProjects = (params) => {
  return apiClient.get('/video-editor/projects', { params })
}

// 获取项目详情
export const getProjectDetail = (id) => {
  return apiClient.get(`/video-editor/projects/${id}`)
}

// 创建项目
export const createProject = (data) => {
  return apiClient.post('/video-editor/projects', data)
}

// 更新项目
export const updateProject = (id, data) => {
  return apiClient.put(`/video-editor/projects/${id}`, data)
}

// 删除项目
export const deleteProject = (id) => {
  return apiClient.delete(`/video-editor/projects/${id}`)
}

// 开始编辑项目
export const startEdit = (id) => {
  return apiClient.post(`/video-editor/projects/${id}/start-edit`)
}

// 导出视频
export const exportVideo = (id, options) => {
  return apiClient.post(`/video-editor/projects/${id}/export`, options)
}

// 获取剪辑任务状态
export const getEditTaskStatus = (taskId) => {
  return apiClient.get(`/video-editor/tasks/${taskId}`)
}

// 取消剪辑任务
export const cancelEditTask = (taskId) => {
  return apiClient.post(`/video-editor/tasks/${taskId}/cancel`)
}

