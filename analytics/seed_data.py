"""
BharatDoc Analytics - Seed Data Generator
Generates realistic fake extraction logs for testing and development
"""

import asyncio
import os
import random
from datetime import datetime, timedelta
from uuid import uuid4

import asyncpg
import numpy as np


# Document type distribution (must sum to 1.0)
DOC_TYPE_DIST = {
    "aadhaar": 0.40,
    "invoice": 0.30,
    "lic_policy": 0.15,
    "handwritten": 0.10,
    "table_doc": 0.05,
}

# Model mapping by document type
MODEL_MAP = {
    "aadhaar": "donut",
    "invoice": "layoutlmv3",
    "lic_policy": "donut",
    "handwritten": "trocr",
    "table_doc": "layoutlmv3",
}

# Scan quality distribution
SCAN_QUALITY_DIST = ["clean", "clean", "clean", "noisy", "noisy", "mixed", "handwritten"]

# Error types
ERROR_TYPES = ["wrong_value", "missing_field", "format_error", "low_confidence"]

# Common field names by document type
FIELD_NAMES = {
    "aadhaar": ["name", "dob", "gender", "aadhaar_number", "address", "photo_present"],
    "invoice": ["invoice_number", "invoice_date", "vendor_name", "grand_total", "gstin", "line_items"],
    "lic_policy": ["policy_number", "holder_name", "sum_assured", "maturity_date", "nominee"],
    "handwritten": ["name", "date", "signature", "address", "phone"],
    "table_doc": ["table_data", "header_row", "total_row", "column_count"],
}


def generate_extraction_log(created_at: datetime) -> dict:
    """Generate a single realistic extraction log"""
    
    # Select document type based on distribution
    doc_type = random.choices(
        list(DOC_TYPE_DIST.keys()),
        weights=list(DOC_TYPE_DIST.values())
    )[0]
    
    # Determine if two-stage pipeline (20% chance for aadhaar and invoice)
    use_two_stage = doc_type in ["aadhaar", "invoice"] and random.random() < 0.20
    
    if use_two_stage:
        model_used = "two_stage"
        # Two-stage: stage1 + stage2 latency
        stage1_latency = int(np.clip(np.random.normal(120, 30), 50, 300))
        stage2_latency = int(np.clip(np.random.normal(130, 40), 60, 350))
        latency_ms = stage1_latency + stage2_latency
        ocr_errors_corrected = random.randint(0, 3)
    else:
        model_used = MODEL_MAP[doc_type]
        # Single stage latency
        latency_ms = int(np.clip(np.random.normal(150, 40), 60, 400))
        stage1_latency = None
        stage2_latency = None
        ocr_errors_corrected = 0
    
    # F1 score: normally distributed around 0.88
    field_f1_score = float(np.clip(np.random.normal(0.88, 0.08), 0.0, 1.0))
    
    # Doc accuracy: true if F1 > 0.85
    doc_accuracy = field_f1_score > 0.85
    
    # Confidence score: correlated with F1 but with some noise
    confidence_score = float(np.clip(field_f1_score + np.random.normal(0, 0.05), 0.0, 1.0))
    
    # File size: 50-500 KB
    file_size_kb = random.randint(50, 500)
    
    # Scan quality
    scan_quality = random.choice(SCAN_QUALITY_DIST)
    
    return {
        "document_type": doc_type,
        "model_used": model_used,
        "field_f1_score": field_f1_score,
        "doc_accuracy": doc_accuracy,
        "latency_ms": latency_ms,
        "stage1_latency_ms": stage1_latency,
        "stage2_latency_ms": stage2_latency,
        "confidence_score": confidence_score,
        "ocr_errors_corrected": ocr_errors_corrected,
        "file_size_kb": file_size_kb,
        "scan_quality": scan_quality,
        "created_at": created_at,
    }


def generate_field_errors(extraction_id: str, doc_type: str, num_errors: int) -> list:
    """Generate field errors for an extraction"""
    errors = []
    field_names = FIELD_NAMES.get(doc_type, ["field_1", "field_2", "field_3"])
    
    for _ in range(num_errors):
        field_name = random.choice(field_names)
        error_type = random.choice(ERROR_TYPES)
        
        # Generate realistic values
        if error_type == "wrong_value":
            expected = "correct_value_123"
            extracted = "wrong_value_456"
        elif error_type == "missing_field":
            expected = "expected_value"
            extracted = None
        elif error_type == "format_error":
            expected = "12/03/1990"
            extracted = "12-03-1990"
        else:  # low_confidence
            expected = None
            extracted = "uncertain_value"
        
        confidence = float(np.clip(np.random.normal(0.5, 0.15), 0.0, 1.0))
        
        errors.append({
            "extraction_id": extraction_id,
            "field_name": field_name,
            "expected_value": expected,
            "extracted_value": extracted,
            "error_type": error_type,
            "confidence": confidence,
        })
    
    return errors


async def seed_database(num_logs: int = 500):
    """Seed the database with realistic fake data"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        print(f"Generating {num_logs} extraction logs...")
        
        total_inserted = 0
        total_with_errors = 0
        total_errors = 0
        
        # Generate logs spread over last 30 days
        now = datetime.utcnow()
        
        for i in range(num_logs):
            # Random timestamp in last 30 days
            days_ago = random.uniform(0, 30)
            created_at = now - timedelta(days=days_ago)
            
            # Generate extraction log
            log = generate_extraction_log(created_at)
            
            # Insert extraction log
            row = await conn.fetchrow(
                """
                INSERT INTO extraction_logs (
                    document_type, model_used, field_f1_score, doc_accuracy,
                    latency_ms, stage1_latency_ms, stage2_latency_ms,
                    confidence_score, ocr_errors_corrected, file_size_kb,
                    scan_quality, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id;
                """,
                log["document_type"],
                log["model_used"],
                log["field_f1_score"],
                log["doc_accuracy"],
                log["latency_ms"],
                log["stage1_latency_ms"],
                log["stage2_latency_ms"],
                log["confidence_score"],
                log["ocr_errors_corrected"],
                log["file_size_kb"],
                log["scan_quality"],
                log["created_at"],
            )
            
            extraction_id = row["id"]
            total_inserted += 1
            
            # 15% chance of having field errors
            if random.random() < 0.15:
                num_errors = random.randint(1, 3)
                errors = generate_field_errors(
                    str(extraction_id),
                    log["document_type"],
                    num_errors
                )
                
                # Insert field errors
                for error in errors:
                    await conn.execute(
                        """
                        INSERT INTO field_errors (
                            extraction_id, field_name, expected_value,
                            extracted_value, error_type, confidence
                        )
                        VALUES ($1, $2, $3, $4, $5, $6);
                        """,
                        extraction_id,
                        error["field_name"],
                        error["expected_value"],
                        error["extracted_value"],
                        error["error_type"],
                        error["confidence"],
                    )
                
                total_with_errors += 1
                total_errors += len(errors)
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Inserted {i + 1}/{num_logs} logs...")
        
        print(f"\n{'='*60}")
        print(f"Seed data generation complete!")
        print(f"{'='*60}")
        print(f"Total extraction logs inserted: {total_inserted}")
        print(f"Logs with field errors: {total_with_errors} ({100*total_with_errors/total_inserted:.1f}%)")
        print(f"Total field errors inserted: {total_errors}")
        print(f"{'='*60}")
        
        # Show some statistics
        print(f"\nDatabase statistics:")
        
        # Count by document type
        rows = await conn.fetch(
            """
            SELECT document_type, COUNT(*) as count
            FROM extraction_logs
            GROUP BY document_type
            ORDER BY count DESC;
            """
        )
        print(f"\nDocument type distribution:")
        for row in rows:
            print(f"  {row['document_type']}: {row['count']}")
        
        # Average F1 by model
        rows = await conn.fetch(
            """
            SELECT model_used, ROUND(AVG(field_f1_score)::numeric, 3) as avg_f1
            FROM extraction_logs
            GROUP BY model_used
            ORDER BY avg_f1 DESC;
            """
        )
        print(f"\nAverage F1 score by model:")
        for row in rows:
            print(f"  {row['model_used']}: {row['avg_f1']}")
        
        # Average latency by model
        rows = await conn.fetch(
            """
            SELECT model_used, ROUND(AVG(latency_ms)::numeric, 1) as avg_latency
            FROM extraction_logs
            GROUP BY model_used
            ORDER BY avg_latency;
            """
        )
        print(f"\nAverage latency by model:")
        for row in rows:
            print(f"  {row['model_used']}: {row['avg_latency']} ms")
    
    finally:
        await conn.close()
        print(f"\nDatabase connection closed.")


if __name__ == "__main__":
    import sys
    
    num_logs = 500
    if len(sys.argv) > 1:
        try:
            num_logs = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number: {sys.argv[1]}, using default 500")
    
    print(f"BharatDoc Analytics - Seed Data Generator")
    print(f"{'='*60}")
    
    asyncio.run(seed_database(num_logs))
