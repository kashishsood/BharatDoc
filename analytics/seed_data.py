"""
Seed analytics database with realistic fake data.

Generates 500 extraction logs with realistic distributions
and field errors for demo purposes.
"""

import asyncio
import os
import random
from datetime import datetime, timedelta
from uuid import uuid4

import asyncpg
import numpy as np


# Document type distributions
DOC_TYPE_WEIGHTS = {
    'aadhaar': 0.40,
    'invoice': 0.30,
    'lic_policy': 0.15,
    'handwritten': 0.10,
    'table_doc': 0.05
}

# Model used by document type
MODEL_BY_DOC_TYPE = {
    'aadhaar': [('donut', 0.80), ('two_stage', 0.20)],
    'invoice': [('layoutlmv3', 0.75), ('llava', 0.25)],
    'lic_policy': [('donut', 0.70), ('two_stage', 0.30)],
    'handwritten': [('trocr', 0.90), ('llava', 0.10)],
    'table_doc': [('layoutlmv3', 0.85), ('two_stage', 0.15)]
}

# Latency by model (mean, std)
LATENCY_BY_MODEL = {
    'donut': (120, 25),
    'layoutlmv3': (95, 20),
    'trocr': (80, 15),
    'llava': (450, 80),
    'two_stage': (250, 50)
}

# Scan quality distribution
SCAN_QUALITY_WEIGHTS = {
    'clean': 0.60,
    'noisy': 0.25,
    'mixed': 0.10,
    'handwritten': 0.05
}

# Field names by document type
FIELD_NAMES = {
    'aadhaar': ['aadhaar_number', 'name', 'dob', 'gender', 'address', 'pincode'],
    'invoice': ['gstin', 'invoice_number', 'date', 'total_amount', 'vendor_name', 'tax_amount'],
    'lic_policy': ['policy_number', 'plan_name', 'premium_amount', 'maturity_date', 'insured_name'],
    'handwritten': ['name', 'date', 'signature', 'amount', 'description'],
    'table_doc': ['header', 'row_count', 'column_names', 'total', 'subtotal']
}

# Error types
ERROR_TYPES = ['wrong_value', 'format_error', 'missing_field', 'low_confidence']
ERROR_TYPE_WEIGHTS = [0.40, 0.30, 0.20, 0.10]


def choose_weighted(options: dict) -> str:
    """Choose randomly based on weights."""
    items = list(options.keys())
    weights = list(options.values())
    return random.choices(items, weights=weights)[0]


def generate_extraction_log() -> dict:
    """Generate a single realistic extraction log."""
    # Choose document type
    doc_type = choose_weighted(DOC_TYPE_WEIGHTS)
    
    # Choose model based on document type
    models, weights = zip(*MODEL_BY_DOC_TYPE[doc_type])
    model_used = random.choices(models, weights=weights)[0]
    
    # Generate F1 score (normal distribution)
    field_f1_score = np.clip(np.random.normal(0.88, 0.07), 0.5, 1.0)
    
    # Doc accuracy based on F1 score
    doc_accuracy = field_f1_score > 0.80
    
    # Generate latency based on model
    mean_latency, std_latency = LATENCY_BY_MODEL[model_used]
    latency_ms = int(np.clip(np.random.normal(mean_latency, std_latency), 50, 2000))
    
    # Stage latencies for two-stage models
    if model_used == 'two_stage':
        stage1_latency_ms = int(latency_ms * 0.4)
        stage2_latency_ms = int(latency_ms * 0.6)
    else:
        stage1_latency_ms = latency_ms
        stage2_latency_ms = None
    
    # Confidence score
    confidence_score = np.clip(np.random.normal(0.85, 0.08), 0.4, 1.0)
    
    # OCR errors corrected (only for two-stage)
    if model_used == 'two_stage':
        ocr_errors_corrected = np.random.poisson(2)
    else:
        ocr_errors_corrected = 0
    
    # Random timestamp in last 30 days
    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
    
    # Scan quality
    scan_quality = choose_weighted(SCAN_QUALITY_WEIGHTS)
    
    # File size
    file_size_kb = random.randint(50, 2000)
    
    return {
        'document_type': doc_type,
        'model_used': model_used,
        'field_f1_score': round(field_f1_score, 3),
        'doc_accuracy': doc_accuracy,
        'latency_ms': latency_ms,
        'stage1_latency_ms': stage1_latency_ms,
        'stage2_latency_ms': stage2_latency_ms,
        'confidence_score': round(confidence_score, 3),
        'ocr_errors_corrected': ocr_errors_corrected,
        'file_size_kb': file_size_kb,
        'scan_quality': scan_quality,
        'created_at': created_at
    }


def generate_field_errors(extraction_id: str, doc_type: str) -> list:
    """Generate 1-3 field errors for an extraction."""
    num_errors = random.randint(1, 3)
    errors = []
    
    available_fields = FIELD_NAMES[doc_type]
    selected_fields = random.sample(available_fields, min(num_errors, len(available_fields)))
    
    for field_name in selected_fields:
        error_type = random.choices(ERROR_TYPES, weights=ERROR_TYPE_WEIGHTS)[0]
        
        errors.append({
            'extraction_id': extraction_id,
            'field_name': field_name,
            'expected_value': 'EXPECTED_VALUE',
            'extracted_value': 'EXTRACTED_VALUE',
            'error_type': error_type,
            'confidence': round(random.uniform(0.3, 0.7), 2)
        })
    
    return errors


async def seed_database():
    """Seed the database with 500 extraction logs."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    print("Generating and inserting 500 extraction logs...")
    
    extraction_ids = []
    field_errors_to_insert = []
    
    for i in range(500):
        log = generate_extraction_log()
        
        # Insert extraction log
        row = await conn.fetchrow("""
            INSERT INTO extraction_logs (
                document_type, model_used, field_f1_score, doc_accuracy, latency_ms,
                stage1_latency_ms, stage2_latency_ms, confidence_score,
                ocr_errors_corrected, file_size_kb, scan_quality, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """,
            log['document_type'],
            log['model_used'],
            log['field_f1_score'],
            log['doc_accuracy'],
            log['latency_ms'],
            log['stage1_latency_ms'],
            log['stage2_latency_ms'],
            log['confidence_score'],
            log['ocr_errors_corrected'],
            log['file_size_kb'],
            log['scan_quality'],
            log['created_at']
        )
        
        extraction_id = row['id']
        extraction_ids.append(extraction_id)
        
        # 20% chance of having field errors
        if random.random() < 0.20:
            errors = generate_field_errors(str(extraction_id), log['document_type'])
            field_errors_to_insert.extend(errors)
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"  Inserted {i + 1} extraction logs...")
    
    print(f"✅ Inserted 500 extraction logs")
    
    # Insert field errors
    print(f"Inserting {len(field_errors_to_insert)} field errors...")
    
    for error in field_errors_to_insert:
        await conn.execute("""
            INSERT INTO field_errors (
                extraction_id, field_name, expected_value, extracted_value,
                error_type, confidence
            )
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            error['extraction_id'],
            error['field_name'],
            error['expected_value'],
            error['extracted_value'],
            error['error_type'],
            error['confidence']
        )
    
    print(f"✅ Inserted {len(field_errors_to_insert)} field errors")
    
    await conn.close()
    
    print("\n" + "=" * 60)
    print("SEED DATA SUMMARY")
    print("=" * 60)
    print(f"Total extraction logs: 500")
    print(f"Total field errors: {len(field_errors_to_insert)}")
    print(f"Date range: Last 30 days")
    print(f"Document types: {list(DOC_TYPE_WEIGHTS.keys())}")
    print(f"Models: {list(LATENCY_BY_MODEL.keys())}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_database())
