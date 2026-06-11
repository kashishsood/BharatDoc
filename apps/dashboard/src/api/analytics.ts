import axios from 'axios'
import type { AnalyticsOverview, DailyStats, ModelComparison, FieldError, LatencyTrend } from '../types'

const BASE = '/api/analytics'

export const analyticsApi = {
  getOverview: (): Promise<AnalyticsOverview> =>
    axios.get(`${BASE}/analytics/overview`).then(r => r.data),

  getDailyStats: (days = 30): Promise<DailyStats[]> =>
    axios.get(`${BASE}/analytics/daily`, { params: { days } }).then(r => r.data),

  getModelComparison: (): Promise<ModelComparison[]> =>
    axios.get(`${BASE}/analytics/model-comparison`).then(r => r.data),

  getFieldErrors: (documentType = 'all', limit = 20): Promise<FieldError[]> =>
    axios.get(`${BASE}/analytics/field-errors`, { 
      params: { document_type: documentType, limit } 
    }).then(r => r.data),

  getLatencyTrend: (days = 7): Promise<LatencyTrend[]> =>
    axios.get(`${BASE}/analytics/latency-trend`, { params: { days } }).then(r => r.data),
}
