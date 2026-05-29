"""
BharatDoc Analytics - SQL Queries
All queries use asyncpg with $1, $2 parameter placeholders
"""

# Insert extraction log
INSERT_EXTRACTION_LOG = """
INSERT INTO extraction_logs (
    document_type, model_used, field_f1_score, doc_accuracy,
    latency_ms, stage1_latency_ms, stage2_latency_ms,
    confidence_score, ocr_errors_corrected, file_size_kb, scan_quality
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING id, created_at;
"""

# Insert field errors (batch)
INSERT_FIELD_ERROR = """
INSERT INTO field_errors (
    extraction_id, field_name, expected_value, extracted_value,
    error_type, confidence
)
VALUES ($1, $2, $3, $4, $5, $6);
"""

# Analytics overview with CTEs
ANALYTICS_OVERVIEW = """
WITH stats AS (
    SELECT
        COUNT(*) as total_extractions,
        AVG(field_f1_score) as avg_f1_score,
        AVG(latency_ms) as avg_latency_ms
    FROM extraction_logs
),
best_model AS (
    SELECT model_used
    FROM extraction_logs
    GROUP BY model_used
    ORDER BY AVG(field_f1_score) DESC
    LIMIT 1
),
worst_doc_type AS (
    SELECT document_type
    FROM extraction_logs
    GROUP BY document_type
    ORDER BY AVG(CASE WHEN doc_accuracy THEN 1.0 ELSE 0.0 END) ASC
    LIMIT 1
),
error_count AS (
    SELECT COUNT(*) as total_errors
    FROM field_errors
)
SELECT
    s.total_extractions,
    ROUND(CAST(s.avg_f1_score AS NUMERIC), 4) as avg_f1_score,
    ROUND(CAST(s.avg_latency_ms AS NUMERIC), 2) as avg_latency_ms,
    COALESCE(bm.model_used, 'N/A') as best_model,
    COALESCE(wd.document_type, 'N/A') as worst_document_type,
    ec.total_errors
FROM stats s
CROSS JOIN best_model bm
CROSS JOIN worst_doc_type wd
CROSS JOIN error_count ec;
"""

# Daily stats with zero-fill for missing days
DAILY_STATS = """
WITH date_series AS (
    SELECT generate_series(
        NOW() - INTERVAL '%s days',
        NOW(),
        '1 day'::interval
    )::date as date
),
daily_data AS (
    SELECT
        DATE(created_at) as date,
        COUNT(*) as count,
        AVG(field_f1_score) as avg_f1,
        AVG(latency_ms) as avg_latency
    FROM extraction_logs
    WHERE created_at >= NOW() - INTERVAL '%s days'
    GROUP BY DATE(created_at)
)
SELECT
    ds.date,
    COALESCE(dd.count, 0) as count,
    ROUND(CAST(COALESCE(dd.avg_f1, 0) AS NUMERIC), 4) as avg_f1,
    ROUND(CAST(COALESCE(dd.avg_latency, 0) AS NUMERIC), 2) as avg_latency
FROM date_series ds
LEFT JOIN daily_data dd ON ds.date = dd.date
ORDER BY ds.date ASC;
"""

# Model comparison with ranking
MODEL_COMPARISON = """
SELECT
    model_used,
    document_type,
    ROUND(CAST(AVG(field_f1_score) AS NUMERIC), 4) as avg_f1,
    ROUND(CAST(AVG(latency_ms) AS NUMERIC), 2) as avg_latency,
    COUNT(*) as total,
    RANK() OVER (
        PARTITION BY document_type
        ORDER BY AVG(field_f1_score) DESC
    ) as rank_in_doc_type
FROM extraction_logs
GROUP BY model_used, document_type
ORDER BY document_type, rank_in_doc_type;
"""

# Field errors analysis with percentage
FIELD_ERRORS_ALL = """
SELECT
    field_name,
    error_type,
    COUNT(*) as count,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        1
    ) as error_pct
FROM field_errors
GROUP BY field_name, error_type
ORDER BY count DESC
LIMIT $1;
"""

FIELD_ERRORS_BY_DOCTYPE = """
SELECT
    fe.field_name,
    fe.error_type,
    COUNT(*) as count,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY el.document_type),
        1
    ) as error_pct
FROM field_errors fe
JOIN extraction_logs el ON fe.extraction_id = el.id
WHERE el.document_type = $1
GROUP BY fe.field_name, fe.error_type
ORDER BY count DESC
LIMIT $2;
"""

# Latency trend by hour
LATENCY_TREND = """
SELECT
    model_used,
    DATE_TRUNC('hour', created_at) as hour,
    ROUND(CAST(AVG(latency_ms) AS NUMERIC), 2) as avg_latency_ms,
    COUNT(*) as sample_count
FROM extraction_logs
WHERE created_at >= NOW() - INTERVAL '%s days'
GROUP BY model_used, DATE_TRUNC('hour', created_at)
ORDER BY hour ASC, model_used;
"""

# Health check query
HEALTH_CHECK = """
SELECT 1 as status;
"""
