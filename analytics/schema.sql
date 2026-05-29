-- BharatDoc Analytics Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table 1: Extraction Logs
CREATE TABLE IF NOT EXISTS extraction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    field_f1_score FLOAT NOT NULL,
    doc_accuracy BOOLEAN NOT NULL,
    latency_ms INTEGER NOT NULL,
    stage1_latency_ms INTEGER,
    stage2_latency_ms INTEGER,
    confidence_score FLOAT NOT NULL,
    ocr_errors_corrected INTEGER DEFAULT 0,
    file_size_kb INTEGER NOT NULL,
    scan_quality VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Table 2: Field Errors
CREATE TABLE IF NOT EXISTS field_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    expected_value TEXT,
    extracted_value TEXT,
    error_type VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_extraction
        FOREIGN KEY (extraction_id)
        REFERENCES extraction_logs(id)
        ON DELETE CASCADE
);

-- Table 3: Model Performance Daily Aggregates
CREATE TABLE IF NOT EXISTS model_performance_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    total_extractions INTEGER NOT NULL,
    avg_f1_score FLOAT NOT NULL,
    avg_latency_ms FLOAT NOT NULL,
    error_rate FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_daily_model_doc
        UNIQUE (date, model_used, document_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_extraction_logs_created_at 
    ON extraction_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_extraction_logs_document_type 
    ON extraction_logs(document_type);

CREATE INDEX IF NOT EXISTS idx_extraction_logs_model_used 
    ON extraction_logs(model_used);

CREATE INDEX IF NOT EXISTS idx_field_errors_extraction_id 
    ON field_errors(extraction_id);

CREATE INDEX IF NOT EXISTS idx_field_errors_field_name 
    ON field_errors(field_name);

CREATE INDEX IF NOT EXISTS idx_model_performance_daily_date 
    ON model_performance_daily(date);

-- Comments for documentation
COMMENT ON TABLE extraction_logs IS 'Logs every document extraction with performance metrics';
COMMENT ON TABLE field_errors IS 'Tracks field-level extraction errors for analysis';
COMMENT ON TABLE model_performance_daily IS 'Daily aggregated model performance metrics';

COMMENT ON COLUMN extraction_logs.field_f1_score IS 'Overall field-level F1 score for this extraction (0-1)';
COMMENT ON COLUMN extraction_logs.doc_accuracy IS 'Whether the full document was correctly extracted';
COMMENT ON COLUMN extraction_logs.stage1_latency_ms IS 'First stage latency (null for single-stage models)';
COMMENT ON COLUMN extraction_logs.stage2_latency_ms IS 'Second stage latency (null for single-stage models)';
COMMENT ON COLUMN extraction_logs.ocr_errors_corrected IS 'Number of OCR errors corrected by stage 2 (two-stage pipeline)';
COMMENT ON COLUMN extraction_logs.scan_quality IS 'Document scan quality: clean, noisy, handwritten, mixed';

COMMENT ON COLUMN field_errors.expected_value IS 'Ground truth value (nullable, only for evaluation mode)';
COMMENT ON COLUMN field_errors.error_type IS 'Error type: wrong_value, missing_field, format_error, low_confidence';
