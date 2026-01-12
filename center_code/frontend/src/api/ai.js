import { apiClient } from './index'

/**
 * AI 功能 API
 */
export const generateCopy = (data) => {
  return apiClient.post('/ai/copy/generate', data)
}

export const getTtsVoices = () => {
  return apiClient.get('/ai/tts/voices')
}

export const synthesizeTts = (data) => {
  return apiClient.post('/ai/tts/synthesize', data)
}

export const generateSubtitle = (data) => {
  return apiClient.post('/ai/subtitle/srt', data)
}

