"""
BharatDoc Analytics Service
FastAPI application for tracking and analyzing document extraction performance
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import queries

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Database connection pool (global)
db_pool: Optional[asyncpg.Pool] = None


# ============================================================================
# Pydantic Models
# ============================================================================

class ExtractionLogCreate(BaseModel):
    """Request model for creating an extraction log"""
    document_type: str = Field(..., max_length=50)
    model_used: str = Field(..., max_length=100)
    field_f1_score: float = Field(..., ge=0.0, le=1.0)
    doc_accuracy: bool
    latency_ms: int = Field(..., gt=0)
    stage1_latency_ms: Optional[int] = Field(None, gt=0)
    stage2_latency_ms: Optional[int] = Field(None, gt=0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    ocr_errors_corrected: int = Field(default=0, ge=0)
    file_size_kb: int = Field(..., gt=0)
    scan_quality: str = Field(..., max_length=20)


class ExtractionLogResponse(BaseModel):
    """Response model for extraction log"""
    id: UUID
    document_type: str
    model_used: str
    field_f1_score: float
    doc_accuracy: bool
    latency_ms: int
    stage1_latency_ms: Optional[int]
    stage2_latency_ms: Optional[int]
    confidence_score: float
    ocr_errors_corrected: int
    file_size_kb: int
    scan_quality: str
    created_at: datetime


class FieldErrorCreate(BaseModel):
    """Request model for creating a field error"""
    field_name: str = Field(..., max_length=100)
    expected_value: Optional[str] = None
    extracted_value: Optional[str] = None
    error_type: str = Field(..., max_length=50)
    confidence: float = Field(..., ge=0.0, le=1.0)


class AnalyticsOverview(BaseModel):
    """Analytics overview response"""
    total_extractions: int
    avg_f1_score: float
    avg_latency_ms: float
    best_model: str
    worst_document_type: str
    total_errors: int


class DailyStats(BaseModel):
    """Daily statistics response"""
    date: str
    count: int
    avg_f1: float
    avg_latency: float


class ModelComparison(BaseModel):
    """Model comparison response"""
    model_used: str
    document_type: str
    avg_f1: float
    avg_latency: float
    total: int
    rank_in_doc_type: int


class FieldErrorStats(BaseModel):
    """Field error statistics response"""
    field_name: str
    error_type: str
    count: int
    error_pct: float


class LatencyTrend(BaseModel):
    """Latency trend response"""
    model_used: str
    hour: datetime
    avg_latency_ms: float
    sample_count: int


# ============================================================================
# Database Connection Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database connection pool"""
    global db_pool
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        raise RuntimeError("DATABASE_URL environment variable is required")
    
    logger.info("Connecting to database...")
    try:
        db_pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool created successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    finally:
        if db_pool:
            logger.info("Closing database connection pool...")
            await db_pool.close()
            logger.info("Database connection pool closed")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="BharatDoc Analytics Service",
    description="Analytics and monitoring for document extraction pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Endpoints
# ============================================================================

@app.post("/extractions", response_model=ExtractionLogResponse, status_code=201)
async def create_extraction_log(log: ExtractionLogCreate):
    """
    Log a new document extraction with performance metrics
    """
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                queries.INSERT_EXTRACTION_LOG,
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
                id=row["id"],
                created_at=row["created_at"],
                **log.dict()
            )
        except Exception as e:
            logger.error(f"Failed to insert extraction log: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/extractions/{extraction_id}/errors", status_code=201)
async def create_field_errors(extraction_id: UUID, errors: List[FieldErrorCreate]):
    """
    Log field-level errors for an extraction
    """
    if not errors:
        raise HTTPException(status_code=400, detail="No errors provided")
    
    async with db_pool.acquire() as conn:
        try:
            # Verify extraction exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM extraction_logs WHERE id = $1)",
                extraction_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Extraction not found")
            
            # Insert all errors
            async with conn.transaction():
                for error in errors:
                    await conn.execute(
                        queries.INSERT_FIELD_ERROR,
                        extraction_id,
                        error.field_name,
                        error.expected_value,
                        error.extracted_value,
                        error.error_type,
                        error.confidence
                    )
            
            return {"inserted": len(errors), "extraction_id": str(extraction_id)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to insert field errors: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_analytics_overview():
    """
    Get overall analytics overview with key metrics
    """
    async with db_pool.acquire() as conn:
        try:
            row = await conn.fetchrow(queries.ANALYTICS_OVERVIEW)
            
            if not row:
                return AnalyticsOverview(
                    total_extractions=0,
                    avg_f1_score=0.0,
                    avg_latency_ms=0.0,
                    best_model="N/A",
                    worst_document_type="N/A",
                    total_errors=0
                )
            
            return AnalyticsOverview(
                total_extractions=row["total_extractions"],
                avg_f1_score=float(row["avg_f1_score"]) if row["avg_f1_score"] else 0.0,
                avg_latency_ms=float(row["avg_latency_ms"]) if row["avg_latency_ms"] else 0.0,
                best_model=row["best_model"],
                worst_document_type=row["worst_document_type"],
                total_errors=row["total_errors"]
            )
        except Exception as e:
            logger.error(f"Failed to fetch analytics overview: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/analytics/daily", response_model=List[DailyStats])
async def get_daily_stats(days: int = Query(default=30, ge=1, le=90)):
    """
    Get daily statistics for the last N days (includes zero-extraction days)
    """
    async with db_pool.acquire() as conn:
        try:
            # Replace %s placeholders with actual days value
            query = queries.DAILY_STATS.replace('%s', str(days))
            rows = await conn.fetch(query)
            
            return [
                DailyStats(
                    date=row["date"].isoformat(),
                    count=row["count"],
                    avg_f1=float(row["avg_f1"]),
                    avg_latency=float(row["avg_latency"])
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch daily stats: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/analytics/model-comparison", response_model=List[ModelComparison])
async def get_model_comparison():
    """
    Compare model performance across document types with ranking
    """
    async with db_pool.acquire() as conn:
        try:
            rows = await conn.fetch(queries.MODEL_COMPARISON)
            
            return [
                ModelComparison(
                    model_used=row["model_used"],
                    document_type=row["document_type"],
                    avg_f1=float(row["avg_f1"]),
                    avg_latency=float(row["avg_latency"]),
                    total=row["total"],
                    rank_in_doc_type=row["rank_in_doc_type"]
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch model comparison: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/analytics/field-errors", response_model=List[FieldErrorStats])
async def get_field_errors(
    document_type: str = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get most common field errors with percentage breakdown
    """
    async with db_pool.acquire() as conn:
        try:
            if document_type == "all":
                rows = await conn.fetch(queries.FIELD_ERRORS_ALL, limit)
            else:
                rows = await conn.fetch(
                    queries.FIELD_ERRORS_BY_DOCTYPE,
                    document_type,
                    limit
                )
            
            return [
                FieldErrorStats(
                    field_name=row["field_name"],
                    error_type=row["error_type"],
                    count=row["count"],
                    error_pct=float(row["error_pct"])
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch field errors: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/analytics/latency-trend", response_model=List[LatencyTrend])
async def get_latency_trend(days: int = Query(default=7, ge=1, le=30)):
    """
    Get hourly latency trend for detecting performance degradation
    """
    async with db_pool.acquire() as conn:
        try:
            query = queries.LATENCY_TREND.replace('%s', str(days))
            rows = await conn.fetch(query)
            
            return [
                LatencyTrend(
                    model_used=row["model_used"],
                    hour=row["hour"],
                    avg_latency_ms=float(row["avg_latency_ms"]),
                    sample_count=row["sample_count"]
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to fetch latency trend: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint with database connectivity test
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval(queries.HEALTH_CHECK)
        
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
