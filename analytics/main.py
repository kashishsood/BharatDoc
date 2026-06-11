"""
BharatDoc Analytics Service
FastAPI application with PostgreSQL backend for extraction analytics.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection pool
db_pool: asyncpg.Pool | None = None


# Pydantic models
class ExtractionLogCreate(BaseModel):
    document_type: str
    model_used: str
    field_f1_score: float | None = None
    doc_accuracy: bool | None = None
    latency_ms: int | None = None
    stage1_latency_ms: int | None = None
    stage2_latency_ms: int | None = None
    confidence_score: float | None = None
    ocr_errors_corrected: int = 0
    file_size_kb: int | None = None
    scan_quality: str = "clean"


class FieldErrorCreate(BaseModel):
    field_name: str
    expected_value: str | None = None
    extracted_value: str | None = None
    error_type: str
    confidence: float | None = None


class ExtractionLogResponse(BaseModel):
    id: UUID
    document_type: str
    model_used: str
    field_f1_score: float | None
    doc_accuracy: bool | None
    latency_ms: int | None
    stage1_latency_ms: int | None
    stage2_latency_ms: int | None
    confidence_score: float | None
    ocr_errors_corrected: int
    file_size_kb: int | None
    scan_quality: str
    created_at: datetime


class AnalyticsOverview(BaseModel):
    total_extractions: int
    avg_f1_score: float
    avg_latency_ms: float
    best_model: str
    worst_document_type: str
    total_errors: int


class DailyStats(BaseModel):
    date: str
    count: int
    avg_f1: float
    avg_latency: float


class ModelComparison(BaseModel):
    model_used: str
    document_type: str
    avg_f1: float
    avg_latency: float
    total: int
    rank_in_doc_type: int


class FieldError(BaseModel):
    field_name: str
    error_type: str
    count: int
    error_pct: float
    document_type: str


class LatencyTrend(BaseModel):
    model_used: str
    hour: datetime
    avg_latency_ms: float
    request_count: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global db_pool
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    
    logger.info("Connecting to database...")
    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        command_timeout=60
    )
    logger.info("Database connection pool created")
    
    yield
    
    logger.info("Closing database connection pool...")
    await db_pool.close()
    logger.info("Database connection pool closed")


app = FastAPI(
    title="BharatDoc Analytics API",
    description="Analytics service for document extraction metrics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/extractions", response_model=ExtractionLogResponse, status_code=201)
async def create_extraction_log(log: ExtractionLogCreate):
    """Insert a new extraction log entry."""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                queries.INSERT_EXTRACTION,
                log.document_type,
                log.model_used,
                log.field_f1_score,
                log.doc_accuracy,
                log.latency_ms,
                log.stage1_latency_ms,
                log.stage2_latency_ms,
                log.confidence_score,
                log.ocr_errors_corrected,
                log.file_size_kb,
                log.scan_quality
            )
            
            return ExtractionLogResponse(
                id=row['id'],
                created_at=row['created_at'],
                **log.model_dump()
            )
    except Exception as e:
        logger.error(f"Failed to insert extraction log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extractions/{extraction_id}/errors", status_code=201)
async def create_field_errors(extraction_id: UUID, errors: List[FieldErrorCreate]):
    """Insert field errors for an extraction."""
    try:
        async with db_pool.acquire() as conn:
            inserted_count = 0
            for error in errors:
                await conn.fetchrow(
                    queries.INSERT_FIELD_ERROR,
                    extraction_id,
                    error.field_name,
                    error.expected_value,
                    error.extracted_value,
                    error.error_type,
                    error.confidence
                )
                inserted_count += 1
            
            return {"inserted": inserted_count}
    except Exception as e:
        logger.error(f"Failed to insert field errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_analytics_overview():
    """Get overall analytics overview."""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(queries.ANALYTICS_OVERVIEW)
            
            return AnalyticsOverview(
                total_extractions=row['total_extractions'] or 0,
                avg_f1_score=float(row['avg_f1_score']) if row['avg_f1_score'] else 0.0,
                avg_latency_ms=float(row['avg_latency_ms']) if row['avg_latency_ms'] else 0.0,
                best_model=row['best_model'],
                worst_document_type=row['worst_document_type'],
                total_errors=row['total_errors'] or 0
            )
    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/daily", response_model=List[DailyStats])
async def get_daily_stats(days: int = Query(30, ge=1, le=90)):
    """Get daily extraction statistics."""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(queries.DAILY_STATS, days)
            
            return [
                DailyStats(
                    date=row['date'].isoformat(),
                    count=row['count'],
                    avg_f1=float(row['avg_f1']) if row['avg_f1'] else 0.0,
                    avg_latency=float(row['avg_latency']) if row['avg_latency'] else 0.0
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/model-comparison", response_model=List[ModelComparison])
async def get_model_comparison():
    """Get model performance comparison."""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(queries.MODEL_COMPARISON)
            
            return [
                ModelComparison(
                    model_used=row['model_used'],
                    document_type=row['document_type'],
                    avg_f1=float(row['avg_f1']) if row['avg_f1'] else 0.0,
                    avg_latency=float(row['avg_latency']) if row['avg_latency'] else 0.0,
                    total=row['total'],
                    rank_in_doc_type=row['rank_in_doc_type']
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get model comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/field-errors", response_model=List[FieldError])
async def get_field_errors(
    document_type: str = Query("all"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get field-level error statistics."""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(queries.FIELD_ERRORS_QUERY, document_type, limit)
            
            return [
                FieldError(
                    field_name=row['field_name'],
                    error_type=row['error_type'],
                    count=row['count'],
                    error_pct=float(row['error_pct']),
                    document_type=row['document_type']
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get field errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/latency-trend", response_model=List[LatencyTrend])
async def get_latency_trend(days: int = Query(7, ge=1, le=30)):
    """Get latency trend over time."""
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(queries.LATENCY_TREND, days)
            
            return [
                LatencyTrend(
                    model_used=row['model_used'],
                    hour=row['hour'],
                    avg_latency_ms=float(row['avg_latency_ms']),
                    request_count=row['request_count']
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get latency trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "disconnected",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
