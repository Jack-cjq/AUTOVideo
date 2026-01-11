import { apiClient } from './index'

export const getPublishPlans = (params) => {
  return apiClient.get('/publish-plans', { params })
}

export const getPublishPlan = (id) => {
  return apiClient.get(`/publish-plans/${id}`)
}

export const createPublishPlan = (data) => {
  return apiClient.post('/publish-plans', data)
}

export const updatePublishPlan = (id, data) => {
  return apiClient.put(`/publish-plans/${id}`, data)
}

export const deletePublishPlan = (id) => {
  return apiClient.delete(`/publish-plans/${id}`)
}

export const addVideoToPlan = (planId, data) => {
  return apiClient.post(`/publish-plans/${planId}/videos`, data)
}

export const savePublishInfo = (planId, data) => {
  return apiClient.post(`/publish-plans/${planId}/save-info`, data)
}

