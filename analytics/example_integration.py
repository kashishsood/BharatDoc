"""
BharatDoc Analytics - Example Gateway Integration
Shows how to integrate analytics logging into the gateway service
"""

import asyncio
from typing import Dict, Optional

from analytics.client import AnalyticsClient


# Example: Integrate into gateway's document processing
async def process_document_with_analytics(
    document_image: bytes,
    analytics_client: AnalyticsClient
) -> Dict:
    """
    Example of processing a document with analytics logging
    
    This shows how the gateway would integrate analytics without
    breaking the main pipeline if analytics is down.
    """
    import time
    
    # Start timing
    start_time = time.time()
    
    # Simulate document classification
    document_type = "aadhaar"  # From CLIP classifier
    
    # Simulate model selection
    model_used = "donut"
    
    # Simulate extraction (this would be actual model inference)
    extraction_result = {
        "name": "Ananya Reddy",
        "dob": "15/08/1990",
        "gender": "Female",
        "aadhaar_number": "7399 6311 3293",
        "address": "123 MG Road, Bangalore",
    }
    
    # Calculate metrics
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Simulate field-level F1 score calculation
    field_f1_score = 0.92
    doc_accuracy = True
    confidence_score = 0.89
    
    # Get file size
    file_size_kb = len(document_image) // 1024
    
    # Determine scan quality (from preprocessing)
    scan_quality = "clean"
    
    # Log to analytics (NEVER RAISES EXCEPTIONS)
    extraction_id = await analytics_client.log_extraction({
        "document_type": document_type,
        "model_used": model_used,
        "field_f1_score": field_f1_score,
        "doc_accuracy": doc_accuracy,
        "latency_ms": latency_ms,
        "confidence_score": confidence_score,
        "file_size_kb": file_size_kb,
        "scan_quality": scan_quality,
    })
    
    # If we have ground truth, log field errors
    if extraction_id:
        # Example: Compare with ground truth (evaluation mode)
        field_errors = []
        
        # Simulate finding an error
        if extraction_result.get("dob") == "15/08/1990":
            # This is correct, no error
            pass
        else:
            # This would be an error
            field_errors.append({
                "field_name": "dob",
                "expected_value": "15/08/1990",
                "extracted_value": extraction_result.get("dob"),
                "error_type": "wrong_value",
                "confidence": 0.75
            })
        
        # Log errors if any (NEVER RAISES EXCEPTIONS)
        if field_errors:
            await analytics_client.log_field_errors(extraction_id, field_errors)
    
    # Return extraction result (main pipeline continues regardless of analytics)
    return {
        "extraction": extraction_result,
        "metadata": {
            "document_type": document_type,
            "model_used": model_used,
            "latency_ms": latency_ms,
            "confidence": confidence_score,
            "analytics_logged": extraction_id is not None,
        }
    }


# Example: Two-stage pipeline with analytics
async def process_with_two_stage_pipeline(
    document_image: bytes,
    analytics_client: AnalyticsClient
) -> Dict:
    """
    Example of two-stage pipeline (Donut + LLM correction) with analytics
    """
    import time
    
    # Stage 1: Donut extraction
    stage1_start = time.time()
    stage1_result = {
        "name": "Ananya Reddy",
        "dob": "15-08-199O",  # OCR error: O instead of 0
        "aadhaar_number": "7399 63ll 3293",  # OCR error: ll instead of 11
    }
    stage1_latency_ms = int((time.time() - stage1_start) * 1000)
    
    # Stage 2: LLM correction
    stage2_start = time.time()
    stage2_result = {
        "name": "Ananya Reddy",
        "dob": "15/08/1990",  # Corrected format and value
        "aadhaar_number": "7399 6311 3293",  # Corrected OCR error
    }
    stage2_latency_ms = int((time.time() - stage2_start) * 1000)
    
    # Count corrections
    ocr_errors_corrected = 2  # dob and aadhaar_number
    
    # Total metrics
    total_latency_ms = stage1_latency_ms + stage2_latency_ms
    field_f1_score = 0.95  # Higher due to corrections
    
    # Log to analytics
    extraction_id = await analytics_client.log_extraction({
        "document_type": "aadhaar",
        "model_used": "two_stage",
        "field_f1_score": field_f1_score,
        "doc_accuracy": True,
        "latency_ms": total_latency_ms,
        "stage1_latency_ms": stage1_latency_ms,
        "stage2_latency_ms": stage2_latency_ms,
        "confidence_score": 0.93,
        "ocr_errors_corrected": ocr_errors_corrected,
        "file_size_kb": len(document_image) // 1024,
        "scan_quality": "noisy",
    })
    
    return {
        "extraction": stage2_result,
        "metadata": {
            "model_used": "two_stage",
            "stage1_latency_ms": stage1_latency_ms,
            "stage2_latency_ms": stage2_latency_ms,
            "total_latency_ms": total_latency_ms,
            "ocr_errors_corrected": ocr_errors_corrected,
            "analytics_logged": extraction_id is not None,
        }
    }


# Example: Batch processing with analytics
async def batch_process_documents(
    documents: list,
    analytics_client: AnalyticsClient
) -> list:
    """
    Example of batch processing multiple documents with analytics
    """
    results = []
    
    for doc in documents:
        result = await process_document_with_analytics(
            doc["image"],
            analytics_client
        )
        results.append(result)
    
    return results


# Example: Main application with analytics
async def main():
    """
    Example main application showing analytics integration
    """
    # Initialize analytics client
    analytics = AnalyticsClient("http://localhost:8002", timeout=5.0)
    
    try:
        # Check if analytics service is healthy
        is_healthy = await analytics.health_check()
        if is_healthy:
            print("✓ Analytics service is healthy")
        else:
            print("⚠ Analytics service is unhealthy (will continue anyway)")
        
        # Simulate document image
        fake_image = b"fake_image_data" * 1000
        
        # Process single document
        print("\n1. Processing single document...")
        result = await process_document_with_analytics(fake_image, analytics)
        print(f"   Result: {result['metadata']}")
        
        # Process with two-stage pipeline
        print("\n2. Processing with two-stage pipeline...")
        result = await process_with_two_stage_pipeline(fake_image, analytics)
        print(f"   Result: {result['metadata']}")
        
        # Batch processing
        print("\n3. Batch processing 3 documents...")
        documents = [{"image": fake_image} for _ in range(3)]
        results = await batch_process_documents(documents, analytics)
        print(f"   Processed {len(results)} documents")
        
        print("\n✓ All processing complete")
        
    finally:
        # Always close the client
        await analytics.close()


if __name__ == "__main__":
    print("="*60)
    print("BharatDoc Analytics - Integration Example")
    print("="*60)
    print("\nThis example shows how to integrate analytics into the gateway.")
    print("The analytics client NEVER raises exceptions - if analytics is")
    print("down, it logs a warning and the main pipeline continues.\n")
    
    asyncio.run(main())
