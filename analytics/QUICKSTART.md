# Analytics Service - Quick Start Guide

Get the BharatDoc Analytics service running in 5 minutes.

## Option 1: Docker Compose (Recommended)

### 1. Start Everything

```bash
# From project root
cd docker
docker-compose up -d

# Check status
docker-compose ps
```

Services started:
- ✅ PostgreSQL on port 5432
- ✅ Analytics on port 8002
- ✅ Gateway on port 8000
- ✅ Inference on port 8001

### 2. Verify Analytics is Running

```bash
curl http://localhost:8002/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2024-..."
}
```

### 3. Seed Test Data

```bash
docker-compose exec analytics python seed_data.py 500
```

This creates 500 fake extraction logs with realistic data.

### 4. Test the API

```bash
# Get overview
curl http://localhost:8002/analytics/overview | jq

# Get daily stats
curl http://localhost:8002/analytics/daily?days=7 | jq

# Model comparison
curl http://localhost:8002/analytics/model-comparison | jq
```

### 5. Run Full Test Suite

```bash
docker-compose exec analytics python test_api.py
```

---

## Option 2: Local Development

### 1. Start PostgreSQL

```bash
docker run -d \
  --name bharatdoc-postgres \
  -e POSTGRES_DB=bharatdoc \
  -e POSTGRES_USER=bharatdoc \
  -e POSTGRES_PASSWORD=bharatdoc \
  -p 5432:5432 \
  postgres:15
```

### 2. Apply Schema

```bash
export DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
psql $DATABASE_URL < analytics/schema.sql
```

### 3. Install Dependencies

```bash
cd analytics
pip install -r requirements.txt
```

### 4. Run Server

```bash
export DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"
uvicorn main:app --reload --port 8002
```

### 5. Seed and Test

```bash
# In another terminal
cd analytics
export DATABASE_URL="postgresql://bharatdoc:bharatdoc@localhost:5432/bharatdoc"

# Seed data
python seed_data.py 500

# Run tests
python test_api.py
```

---

## Quick API Examples

### Log an Extraction

```bash
curl -X POST http://localhost:8002/extractions \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "aadhaar",
    "model_used": "donut",
    "field_f1_score": 0.92,
    "doc_accuracy": true,
    "latency_ms": 145,
    "confidence_score": 0.89,
    "file_size_kb": 234,
    "scan_quality": "clean"
  }'
```

### Log Field Errors

```bash
# Use the extraction_id from above
curl -X POST http://localhost:8002/extractions/{extraction_id}/errors \
  -H "Content-Type: application/json" \
  -d '[
    {
      "field_name": "dob",
      "error_type": "format_error",
      "extracted_value": "15-08-1990",
      "expected_value": "15/08/1990",
      "confidence": 0.75
    }
  ]'
```

### Get Analytics

```bash
# Overview
curl http://localhost:8002/analytics/overview

# Daily stats (last 30 days)
curl http://localhost:8002/analytics/daily?days=30

# Model comparison with ranking
curl http://localhost:8002/analytics/model-comparison

# Top field errors
curl "http://localhost:8002/analytics/field-errors?document_type=aadhaar&limit=10"

# Latency trend (hourly)
curl http://localhost:8002/analytics/latency-trend?days=7
```

---

## Integration with Gateway

### Python Client

```python
from analytics.client import AnalyticsClient

# Initialize
analytics = AnalyticsClient("http://localhost:8002")

# Log extraction (never raises exceptions)
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

# Log errors (optional)
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

## Troubleshooting

### Analytics service won't start

```bash
# Check logs
docker-compose logs analytics

# Common issue: Database not ready
# Solution: Wait 10 seconds and try again
docker-compose restart analytics
```

### Database connection failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U bharatdoc -d bharatdoc -c "SELECT 1;"
```

### No data in analytics

```bash
# Seed test data
docker-compose exec analytics python seed_data.py 500

# Verify
curl http://localhost:8002/analytics/overview
```

---

## Next Steps

1. **Integrate with Gateway**: See `example_integration.py`
2. **Set up Monitoring**: Connect to Grafana/Prometheus
3. **Configure Alerts**: Set up alerts for latency spikes
4. **Review Queries**: Check `queries.py` for custom analytics

---

## Useful Commands

```bash
# View all logs
docker-compose logs -f analytics

# Restart service
docker-compose restart analytics

# Open database shell
docker-compose exec postgres psql -U bharatdoc -d bharatdoc

# Run seed script with custom count
docker-compose exec analytics python seed_data.py 1000

# Run integration example
docker-compose exec analytics python example_integration.py
```

---

**You're ready!** The analytics service is now tracking all document extractions.
