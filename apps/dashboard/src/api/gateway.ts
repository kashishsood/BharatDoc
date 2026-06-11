import axios from 'axios'
import type { ExtractionResult } from '../types'

export const gatewayApi = {
  uploadDocument: async (file: File): Promise<ExtractionResult> => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await axios.post('/api/gateway/extract', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    return response.data
  }
}
