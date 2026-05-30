import axios from 'axios';
import type { ExtractionResult } from '../types';

const api = axios.create({
  baseURL: '/api/gateway',
  timeout: 30000,
});

export const uploadDocument = async (file: File): Promise<ExtractionResult> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<ExtractionResult>('/extractions', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
