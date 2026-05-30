import axios from 'axios';
import type {
  AnalyticsOverview,
  DailyStats,
  ModelComparison,
  FieldError,
  LatencyTrend
} from '../types';

const api = axios.create({
  baseURL: '/api/analytics',
  timeout: 10000,
});

export const getOverview = async (): Promise<AnalyticsOverview> => {
  const response = await api.get<AnalyticsOverview>('/overview');
  return response.data;
};

export const getDailyStats = async (days: number = 30): Promise<DailyStats[]> => {
  const response = await api.get<DailyStats[]>('/daily', {
    params: { days }
  });
  return response.data;
};

export const getModelComparison = async (): Promise<ModelComparison[]> => {
  const response = await api.get<ModelComparison[]>('/model-comparison');
  return response.data;
};

export const getFieldErrors = async (documentType: string = 'all'): Promise<FieldError[]> => {
  const response = await api.get<FieldError[]>('/field-errors', {
    params: { document_type: documentType }
  });
  return response.data;
};

export const getLatencyTrend = async (days: number = 7): Promise<LatencyTrend[]> => {
  const response = await api.get<LatencyTrend[]>('/latency-trend', {
    params: { days }
  });
  return response.data;
};
