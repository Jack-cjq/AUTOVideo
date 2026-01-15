import { apiClient } from './index'

export const getVideos = (params) => {
  return apiClient.get('/video-library', { params })
}

export const getVideo = (id) => {
  return apiClient.get(`/video-library/${id}`)
}

export const uploadVideo = (data) => {
  // 如果data是FormData，说明是文件上传
  if (data instanceof FormData) {
    return apiClient.post('/video-library', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
  // 否则是JSON数据
  return apiClient.post('/video-library', data)
}

export const updateVideo = (id, data) => {
  return apiClient.put(`/video-library/${id}`, data)
}

export const deleteVideo = (id) => {
  return apiClient.delete(`/video-library/${id}`)
}

