-- BharatDoc Analytics Database Schema
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Main extraction logs table
CREATE TABLE IF NOT EXISTS extraction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    field_f1_score FLOAT,
    doc_accuracy BOOLEAN,
    latency_ms INTEGER,
    stage1_latency_ms INTEGER,
    stage2_latency_ms INTEGER,
    confidence_score FLOAT,
    ocr_errors_corrected INTEGER DEFAULT 0,
    file_size_kb INTEGER,
    scan_quality VARCHAR(20) DEFAULT 'clean',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Field-level errors table
CREATE TABLE IF NOT EXISTS field_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extraction_logs(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    expected_value TEXT,
    extracted_value TEXT,
    error_type VARCHAR(50) NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily aggregated performance metrics
CREATE TABLE IF NOT EXISTS model_performance_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    total_extractions INTEGER DEFAULT 0,
    avg_f1_score FLOAT,
    avg_latency_ms FLOAT,
    error_rate FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, model_used, document_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_extraction_logs_created_at ON extraction_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_document_type ON extraction_logs(document_type);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_model_used ON extraction_logs(model_used);
CREATE INDEX IF NOT EXISTS idx_field_errors_extraction_id ON field_errors(extraction_id);
CREATE INDEX IF NOT EXISTS idx_field_errors_field_name ON field_errors(field_name);
