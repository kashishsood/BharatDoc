export interface AnalyticsOverview {
  total_extractions: number;
  avg_f1_score: number;
  avg_latency_ms: number;
  best_model: string;
  worst_document_type: string;
  total_errors: number;
}

export interface DailyStats {
  date: string;
  count: number;
  avg_f1: number;
  avg_latency: number;
}

export interface ModelComparison {
  model_used: string;
  document_type: string;
  avg_f1: number;
  avg_latency: number;
  total: number;
  rank_in_doc_type: number;
}

export interface FieldError {
  field_name: string;
  error_type: string;
  count: number;
  error_pct: number;
}

export interface LatencyTrend {
  model_used: string;
  hour: string;
  avg_latency_ms: number;
}

export interface ExtractionResult {
  document_type: string;
  model_used: string;
  confidence_score: number;
  latency_ms: number;
  extracted_fields: Record<string, string | number>;
}
