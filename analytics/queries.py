"""
SQL query constants for analytics service.

All queries use parameterized syntax ($1, $2, etc.) for asyncpg.
"""

INSERT_EXTRACTION = """
INSERT INTO extraction_logs (
    document_type, model_used, field_f1_score, doc_accuracy, latency_ms,
    stage1_latency_ms, stage2_latency_ms, confidence_score, 
    ocr_errors_corrected, file_size_kb, scan_quality
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING id, created_at
"""

INSERT_FIELD_ERROR = """
INSERT INTO field_errors (
    extraction_id, field_name, expected_value, extracted_value, 
    error_type, confidence
)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id
"""

ANALYTICS_OVERVIEW = """
WITH stats AS (
    SELECT 
        COUNT(*) as total_extractions,
        ROUND(AVG(field_f1_score)::numeric, 3) as avg_f1_score,
        ROUND(AVG(latency_ms)::numeric, 0) as avg_latency_ms
    FROM extraction_logs
),
best_model AS (
    SELECT model_used
    FROM extraction_logs
    GROUP BY model_used
    ORDER BY AVG(field_f1_score) DESC NULLS LAST
    LIMIT 1
),
worst_doc AS (
    SELECT document_type
    FROM extraction_logs
    GROUP BY document_type
    ORDER BY AVG(CASE WHEN doc_accuracy THEN 1.0 ELSE 0.0 END) ASC NULLS LAST
    LIMIT 1
),
error_count AS (
    SELECT COUNT(*) as total_errors FROM field_errors
)
SELECT 
    s.total_extractions,
    s.avg_f1_score,
    s.avg_latency_ms,
    COALESCE(bm.model_used, 'N/A') as best_model,
    COALESCE(wd.document_type, 'N/A') as worst_document_type,
    ec.total_errors
FROM stats s
CROSS JOIN best_model bm
CROSS JOIN worst_doc wd
CROSS JOIN error_count ec
"""

DAILY_STATS = """
WITH date_series AS (
    SELECT generate_series(
        NOW() - ($1 || ' days')::INTERVAL,
        NOW(),
        '1 day'::INTERVAL
    )::DATE as date
),
daily_data AS (
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as count,
        ROUND(AVG(field_f1_score)::numeric, 3) as avg_f1,
        ROUND(AVG(latency_ms)::numeric, 0) as avg_latency
    FROM extraction_logs
    WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
    GROUP BY DATE(created_at)
)
SELECT 
    ds.date,
    COALESCE(dd.count, 0) as count,
    COALESCE(dd.avg_f1, 0) as avg_f1,
    COALESCE(dd.avg_latency, 0) as avg_latency
FROM date_series ds
LEFT JOIN daily_data dd ON ds.date = dd.date
ORDER BY ds.date ASC
"""

MODEL_COMPARISON = """
SELECT 
    model_used,
    document_type,
    ROUND(AVG(field_f1_score)::numeric, 3) as avg_f1,
    ROUND(AVG(latency_ms)::numeric, 0) as avg_latency,
    COUNT(*) as total,
    RANK() OVER (
        PARTITION BY document_type 
        ORDER BY AVG(field_f1_score) DESC NULLS LAST
    ) as rank_in_doc_type
FROM extraction_logs
GROUP BY model_used, document_type
ORDER BY document_type, rank_in_doc_type
"""

FIELD_ERRORS_QUERY = """
SELECT 
    fe.field_name,
    fe.error_type,
    COUNT(*) as count,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY el.document_type),
        1
    ) as error_pct,
    el.document_type
FROM field_errors fe
JOIN extraction_logs el ON fe.extraction_id = el.id
WHERE ($1 = 'all' OR el.document_type = $1)
GROUP BY fe.field_name, fe.error_type, el.document_type
ORDER BY count DESC
LIMIT $2
"""

LATENCY_TREND = """
SELECT 
    model_used,
    DATE_TRUNC('hour', created_at) as hour,
    ROUND(AVG(latency_ms)::numeric, 0) as avg_latency_ms,
    COUNT(*) as request_count
FROM extraction_logs
WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
GROUP BY model_used, DATE_TRUNC('hour', created_at)
ORDER BY hour ASC, model_used
"""
