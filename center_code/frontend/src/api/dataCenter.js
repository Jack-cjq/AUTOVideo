import { apiClient } from './index'

export const getVideoStats = (params) => {
  return apiClient.get('/data-center/video-stats', { params })
}

export const getAccountStats = (params) => {
  return apiClient.get('/data-center/account-stats', { params })
}

export const getAccountRanking = (params) => {
  return apiClient.get('/data-center/account-ranking', { params })
}

export const getAccountVideos = (params) => {
  return apiClient.get('/data-center/account-videos', { params })
}

// 从抖音获取视频详细数据
export const fetchVideoDataFromDouyin = (data) => {
  return apiClient.post('/data-center/fetch-video-data', data)
}