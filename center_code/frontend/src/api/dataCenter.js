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
