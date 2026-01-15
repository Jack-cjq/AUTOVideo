import { apiClient } from './index'

/**
 * 素材管理 API
 */
export const uploadMaterial = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/material/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const getMaterials = (params) => {
  return apiClient.get('/materials', { params })
}

export const clearMaterials = () => {
  return apiClient.post('/materials/clear', { confirm: true })
}

export const deleteMaterial = (materialId, filePath, force = false) => {
  return apiClient.post('/delete-material', {
    material_id: materialId,
    file_path: filePath,
    force
  })
}

export const getOutputs = () => {
  return apiClient.get('/outputs')
}

export const deleteOutput = (filename, cosKey = null) => {
  return apiClient.post('/output/delete', { 
    filename,
    cos_key: cosKey  // 如果是从COS获取的列表，传递cos_key
  })
}

export const downloadVideo = (filename) => {
  return apiClient.get(`/download/video/${filename}`, {
    responseType: 'blob'
  })
}

