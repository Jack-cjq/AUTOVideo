import { apiClient } from './index'

export const getMerchants = (params) => {
  return apiClient.get('/merchants', { params })
}

export const getMerchant = (id) => {
  return apiClient.get(`/merchants/${id}`)
}

export const createMerchant = (data) => {
  return apiClient.post('/merchants', data)
}

export const updateMerchant = (id, data) => {
  return apiClient.put(`/merchants/${id}`, data)
}

export const deleteMerchant = (id) => {
  return apiClient.delete(`/merchants/${id}`)
}

