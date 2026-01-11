import { apiClient } from './index'

export const getVideos = (params) => {
  return apiClient.get('/video-library', { params })
}

export const getVideo = (id) => {
  return apiClient.get(`/video-library/${id}`)
}

export const uploadVideo = (data) => {
  return apiClient.post('/video-library', data)
}

export const updateVideo = (id, data) => {
  return apiClient.put(`/video-library/${id}`, data)
}

export const deleteVideo = (id) => {
  return apiClient.delete(`/video-library/${id}`)
}

