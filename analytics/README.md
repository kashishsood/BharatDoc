# BharatDoc Analytics Service

Analytics and monitoring service for tracking document extraction performance.

## Features

- **Extraction Logging**: Track every document extraction with performance metrics
- **Field Error Tracking**: Log field-level errors for analysis
- **Performance Analytics**: Compare models, track trends, identify issues
- **Daily Aggregation**: Automatic daily statistics
- **Latency Monitoring**: Hourly latency trends for detecting degradation
- **Never-Fail Client**: Analytics failures never break the main pipeline

## Architecture

```
┌─────────────┐
│   Gateway   │
│  (FastAPI)  │
└──────┬──────┘
       │ HTTP POST (async, non-blocking)
       ▼
┌─────────────┐      ┌──────────────┐
│  Analytics  │◄────►│  PostgreSQL  │
│   Service   │      │   Database   │
│  (FastAPI)  │      └──────────────┘
└─────────────┘
       │
       ▼
  Dashboards / Reports
```

## Database Schema

### Tables

1. **extraction_logs** - Every document extraction with metrics
2. **field_errors** - Field-level error tracking
3. **model_performance_daily** - Daily aggregated statistics

See `schema.sql` for complete schema.

## API Endpoints

### Logging

- `POST /extractions` - Log a new extraction
- `POST /extractions/{id}/errors` - Log field errors

### Analytics

- `GET /analytics/overview` - Overall statistics
- `GET /analytics/daily?days=30` - Daily stats (with zero-fill)
- `GET /analytics/model-comparison` - Compare models with ranking
- `GET /analytics/field-errors?document_type=all&limit=20` - Common errors
- `GET /analytics/latency-trend?days=7` - Hourly latency trends

### Health

- `GET /health` - Health check with DB connectivity test

## Quick Start

### 1. Start with Docker Compose

```bash
# From project root
docker-compose -f docker/docker-compose.yml up -d

# Check logs
docker-compose -f docker/docker-compose.yml logs -f analytics
```

The analytics service will be available at `http://localhost:8002`

### 2. Initialize Database

The schema is automatically applied on first startup via `docker-entrypoint-initdb.d`.

### 3. Seed Test Data

```bash
# Generate 500 fake extraction logs
docker-compose -f docker/docker-compose.yml exec analytics python seed_data.py

# Or specify custom count
docker-compose -f docker/docker-compose.yml exec analytics python seed_data.py 1000
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8002/health

# Get overview
curl http://localhost:8002/analytics/overview

# Get daily stats
curl http://localhost:8002/analytics/daily?days=7

# Model comparison
curl http://localhost:8002/analytics/model-comparison

# Field errors
curl http://localhost:8002/analytics/field-errors?document_type=aadhaar&limit=10
```

## Integration with Gateway

### Using the Client

```python
from analytics.client import AnalyticsClient

# Initialize client
analytics = AnalyticsClient("http://analytics:8002")

# Log an extraction (never raises exceptions)
extraction_id = await analytics.log_extraction({
    "document_type": "aadhaar",
    "model_used": "donut",
    "field_f1_score": 0.92,
    "doc_accuracy": True,
    "latency_ms": 145,
    "confidence_score": 0.89,
    "file_size_kb": 234,
    "scan_quality": "clean"
})

# Log field errors (optional)
if extraction_id:
    await analytics.log_field_errors(extraction_id, [
        {
            "field_name": "dob",
            "error_type": "format_error",
            "extracted_value": "15-08-1990",
            "expected_value": "15/08/1990",
            "confidence": 0.75
        }
    ])

# Close client when done
await analytics.close()
```

### Never-Fail Guarantee

The analytics client **never raises exceptions**. If the analytics service is down:
- Logs a warning
- Returns `None` or `False`
- Main pipeline continues normally

This ensures analytics failures never break document extraction.

## Development

### Local Setup

```bash
# Install dependencies
cd analytics
pip install -r requirements.txt

# Set database URL
export DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"

# Apply schema
psql $DATABASE_URL < schema.sql

# Run server
uvicorn main:app --reload --port 8002
```

### Run Tests

```bash
# Seed test data
python seed_data.py 100

# Test endpoints
curl http://localhost:8002/health
curl http://localhost:8002/analytics/overview
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

## Performance

- **Connection Pool**: 2-10 connections
- **Query Timeout**: 60 seconds
- **Async I/O**: Non-blocking database operations
- **Indexes**: Optimized for common queries

## Monitoring

The analytics service exposes:
- Health check endpoint for monitoring
- Structured JSON logs
- Database connection status

Integrate with Prometheus/Grafana for visualization.

## SQL Queries

All SQL queries are in `queries.py` with:
- Parameterized queries ($1, $2) for safety
- Window functions for ranking and percentages
- CTEs for complex analytics
- Zero-fill for missing days in time series

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose -f docker/docker-compose.yml ps postgres

# Check logs
docker-compose -f docker/docker-compose.yml logs postgres

# Test connection
psql postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc
```

### Analytics Service Not Starting

```bash
# Check logs
docker-compose -f docker/docker-compose.yml logs analytics

# Verify DATABASE_URL is set
docker-compose -f docker/docker-compose.yml exec analytics env | grep DATABASE_URL
```

### Slow Queries

```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM extraction_logs WHERE created_at > NOW() - INTERVAL '7 days';

-- Rebuild indexes if needed
REINDEX TABLE extraction_logs;
```

## License

MIT
