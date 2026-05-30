# ✅ Analytics Service - Complete Implementation

## 🎊 What Was Built

A **production-ready analytics service** for tracking and analyzing document extraction performance in BharatDoc.

### Repository
**https://github.com/kashishsood/BharatDoc**

---

## 📁 Files Created (15 files)

### Core Service
1. **`analytics/schema.sql`** - Complete PostgreSQL schema with 3 tables, indexes, comments
2. **`analytics/queries.py`** - All SQL queries with window functions and CTEs
3. **`analytics/main.py`** - FastAPI application with 8 endpoints
4. **`analytics/client.py`** - Never-fail async HTTP client for gateway integration
5. **`analytics/__init__.py`** - Package initialization

### Data & Testing
6. **`analytics/seed_data.py`** - Realistic fake data generator (500+ logs)
7. **`analytics/test_api.py`** - Complete API test suite
8. **`analytics/example_integration.py`** - Gateway integration examples

### Docker & Deployment
9. **`analytics/Dockerfile`** - Python 3.11-slim with health checks
10. **`analytics/requirements.txt`** - FastAPI, asyncpg, httpx, numpy
11. **`docker/docker-compose.yml`** - Updated with analytics + PostgreSQL

### Documentation
12. **`analytics/README.md`** - Complete service documentation
13. **`analytics/QUICKSTART.md`** - 5-minute setup guide
14. **`analytics/Makefile`** - Common commands
15. **`analytics/.env.example`** - Environment variables template

---

## 🗄️ Database Schema

### Table 1: `extraction_logs`
Tracks every document extraction with performance metrics:
- Document type, model used, F1 score, accuracy
- Latency (total, stage1, stage2 for two-stage pipelines)
- Confidence score, OCR errors corrected
- File size, scan quality
- Timestamps

### Table 2: `field_errors`
Field-level error tracking:
- Field name, expected/extracted values
- Error type (wrong_value, missing_field, format_error, low_confidence)
- Confidence score
- Foreign key to extraction_logs with CASCADE delete

### Table 3: `model_performance_daily`
Daily aggregated statistics:
- Date, model, document type
- Total extractions, avg F1, avg latency, error rate
- Unique constraint on (date, model, document_type)

### Indexes
- `extraction_logs(created_at)` - Time-based queries
- `extraction_logs(document_type)` - Document filtering
- `extraction_logs(model_used)` - Model filtering
- `field_errors(extraction_id)` - Join performance
- `field_errors(field_name)` - Error analysis

---

## 🚀 API Endpoints

### Logging Endpoints

**POST /extractions**
- Log a new extraction with metrics
- Returns extraction_id and created_at
- Status 201

**POST /extractions/{id}/errors**
- Log field-level errors
- Accepts array of errors
- Returns count of inserted errors
- Status 201

### Analytics Endpoints

**GET /analytics/overview**
- Total extractions, avg F1, avg latency
- Best model (highest F1)
- Worst document type (lowest accuracy)
- Total field errors
- Uses CTEs for single-query efficiency

**GET /analytics/daily?days=30**
- Daily statistics for last N days (1-90)
- **Zero-fills missing days** (shows days with 0 extractions)
- Returns date, count, avg_f1, avg_latency

**GET /analytics/model-comparison**
- Compare models across document types
- **Uses RANK() window function** to rank models within each doc type
- Returns model, doc_type, avg_f1, avg_latency, total, rank

**GET /analytics/field-errors?document_type=all&limit=20**
- Most common field errors
- **Uses window function for percentage**: `COUNT(*) / SUM(COUNT(*)) OVER ()`
- Filter by document type or "all"
- Returns field_name, error_type, count, error_pct

**GET /analytics/latency-trend?days=7**
- Hourly average latency for last N days
- Groups by hour using `DATE_TRUNC('hour', created_at)`
- Useful for detecting performance degradation
- Returns model, hour, avg_latency_ms, sample_count

**GET /health**
- Health check with actual DB connectivity test
- Returns status, database, timestamp

---

## 🔌 Client Integration

### Never-Fail Guarantee

The `AnalyticsClient` **never raises exceptions**:
- If analytics service is down → logs warning, returns None
- If request times out → logs warning, returns None
- If any error occurs → logs warning, returns None

**Main pipeline never fails due to analytics being unavailable.**

### Usage Example

```python
from analytics.client import AnalyticsClient

# Initialize
analytics = AnalyticsClient("http://analytics:8002", timeout=5.0)

# Log extraction (never raises)
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

# Log errors (optional, never raises)
if extraction_id:
    await analytics.log_field_errors(extraction_id, [
        {
            "field_name": "dob",
            "error_type": "format_error",
            "extracted_value": "15-08-1990",
            "confidence": 0.75
        }
    ])

# Close when done
await analytics.close()
```

---

## 🐳 Docker Integration

### Services Added

**analytics** (port 8002):
- FastAPI service
- Health checks every 30s
- Depends on postgres
- 2 uvicorn workers

**postgres** (port 5432):
- PostgreSQL 15
- Persistent volume
- Auto-applies schema on first startup
- Health checks with pg_isready

### Start Everything

```bash
cd docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f analytics
```

---

## 📊 SQL Query Features

### Window Functions

**Ranking models within document types:**
```sql
RANK() OVER (
    PARTITION BY document_type
    ORDER BY AVG(field_f1_score) DESC
) as rank_in_doc_type
```

**Percentage calculations:**
```sql
ROUND(
    100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY document_type),
    1
) as error_pct
```

### CTEs (Common Table Expressions)

**Analytics overview** uses 4 CTEs:
- `stats` - Overall statistics
- `best_model` - Highest avg F1
- `worst_doc_type` - Lowest accuracy
- `error_count` - Total errors

**Daily stats** uses CTE with `generate_series`:
- Generates all dates in range
- LEFT JOIN with actual data
- Zero-fills missing days

### Parameterized Queries

All queries use `$1, $2, ...` placeholders for safety:
```python
await conn.fetchrow(query, param1, param2, param3)
```

---

## 🧪 Testing

### Seed Test Data

```bash
# Generate 500 realistic logs
docker-compose exec analytics python seed_data.py 500

# Custom count
docker-compose exec analytics python seed_data.py 2000
```

**Data Distribution:**
- 40% aadhaar, 30% invoice, 15% lic_policy, 10% handwritten, 5% table_doc
- F1 scores: normal distribution around 0.88 (std 0.08)
- Latency: 150ms avg for single-stage, 250ms for two-stage
- 15% of logs have 1-3 field errors
- Spread over last 30 days

### Run Tests

```bash
# Complete API test suite
docker-compose exec analytics python test_api.py

# Integration examples
docker-compose exec analytics python example_integration.py
```

---

## 📈 Use Cases

### 1. Model Performance Comparison

```bash
curl http://localhost:8002/analytics/model-comparison
```

See which models perform best for each document type with rankings.

### 2. Latency Monitoring

```bash
curl http://localhost:8002/analytics/latency-trend?days=7
```

Detect performance degradation over time (hourly granularity).

### 3. Error Analysis

```bash
curl "http://localhost:8002/analytics/field-errors?document_type=aadhaar&limit=10"
```

Identify most common field extraction errors with percentages.

### 4. Daily Tracking

```bash
curl http://localhost:8002/analytics/daily?days=30
```

Track extraction volume and quality over time (includes zero-extraction days).

### 5. Two-Stage Pipeline Analysis

Log two-stage extractions with:
- `stage1_latency_ms` - First stage (e.g., Donut)
- `stage2_latency_ms` - Second stage (e.g., LLM correction)
- `ocr_errors_corrected` - How many fields were fixed

---

## 🎯 Quick Start

### 1. Start Services

```bash
cd docker
docker-compose up -d
```

### 2. Verify Health

```bash
curl http://localhost:8002/health
```

### 3. Seed Data

```bash
docker-compose exec analytics python seed_data.py 500
```

### 4. Test API

```bash
curl http://localhost:8002/analytics/overview | jq
```

### 5. Run Full Tests

```bash
docker-compose exec analytics python test_api.py
```

**Done!** Analytics service is tracking all extractions.

---

## 📚 Documentation

- **`analytics/README.md`** - Complete service documentation
- **`analytics/QUICKSTART.md`** - 5-minute setup guide
- **`analytics/example_integration.py`** - Integration examples
- **`analytics/test_api.py`** - API test examples

---

## ✨ Key Features Summary

| Feature | Status |
|---------|--------|
| PostgreSQL schema with 3 tables | ✅ |
| 8 FastAPI endpoints | ✅ |
| Never-fail async client | ✅ |
| Window functions (RANK, percentages) | ✅ |
| CTEs for complex queries | ✅ |
| Zero-fill for time series | ✅ |
| Docker integration | ✅ |
| Health checks | ✅ |
| Seed data generator | ✅ |
| Complete test suite | ✅ |
| Integration examples | ✅ |
| Comprehensive documentation | ✅ |

---

## 🎊 Success!

The analytics service is **fully implemented and deployed**:

✅ **Database**: PostgreSQL with optimized schema and indexes
✅ **API**: 8 endpoints with advanced SQL queries
✅ **Client**: Never-fail integration for gateway
✅ **Docker**: Complete docker-compose setup
✅ **Testing**: Seed data + test suite + examples
✅ **Documentation**: README + QUICKSTART + examples

**Repository**: https://github.com/kashishsood/BharatDoc

**View the code**: https://github.com/kashishsood/BharatDoc/tree/main/analytics

---

*Generated: 2026-05-29*
*All files complete - no placeholders, no TODOs*
