"""
BharatDoc Analytics - API Test Script
Tests all endpoints with realistic data
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8002"


async def test_health():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("Testing: GET /health")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    print("✓ Health check passed")


async def test_create_extraction():
    """Test creating an extraction log"""
    print("\n" + "="*60)
    print("Testing: POST /extractions")
    print("="*60)
    
    extraction_data = {
        "document_type": "aadhaar",
        "model_used": "donut",
        "field_f1_score": 0.92,
        "doc_accuracy": True,
        "latency_ms": 145,
        "stage1_latency_ms": None,
        "stage2_latency_ms": None,
        "confidence_score": 0.89,
        "ocr_errors_corrected": 0,
        "file_size_kb": 234,
        "scan_quality": "clean"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/extractions",
            json=extraction_data
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        assert response.status_code == 201
        assert "id" in data
        extraction_id = data["id"]
    
    print(f"✓ Extraction created with ID: {extraction_id}")
    return extraction_id


async def test_create_field_errors(extraction_id):
    """Test creating field errors"""
    print("\n" + "="*60)
    print(f"Testing: POST /extractions/{extraction_id}/errors")
    print("="*60)
    
    errors = [
        {
            "field_name": "dob",
            "expected_value": "15/08/1990",
            "extracted_value": "15-08-1990",
            "error_type": "format_error",
            "confidence": 0.75
        },
        {
            "field_name": "aadhaar_number",
            "expected_value": "1234 5678 9012",
            "extracted_value": "1234 5678 901",
            "error_type": "wrong_value",
            "confidence": 0.82
        }
    ]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/extractions/{extraction_id}/errors",
            json=errors
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        assert response.status_code == 201
        assert data["inserted"] == 2
    
    print("✓ Field errors created")


async def test_analytics_overview():
    """Test analytics overview"""
    print("\n" + "="*60)
    print("Testing: GET /analytics/overview")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/analytics/overview")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        assert response.status_code == 200
    
    print("✓ Analytics overview retrieved")


async def test_daily_stats():
    """Test daily statistics"""
    print("\n" + "="*60)
    print("Testing: GET /analytics/daily?days=7")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/analytics/daily?days=7")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {len(data)} days of data")
        if data:
            print(f"Sample (first 3 days):")
            for day in data[:3]:
                print(f"  {day}")
        assert response.status_code == 200
    
    print("✓ Daily stats retrieved")


async def test_model_comparison():
    """Test model comparison"""
    print("\n" + "="*60)
    print("Testing: GET /analytics/model-comparison")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/analytics/model-comparison")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {len(data)} model-document combinations")
        if data:
            print(f"Sample (first 3):")
            for item in data[:3]:
                print(f"  {item}")
        assert response.status_code == 200
    
    print("✓ Model comparison retrieved")


async def test_field_errors():
    """Test field errors analysis"""
    print("\n" + "="*60)
    print("Testing: GET /analytics/field-errors?document_type=all&limit=10")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/analytics/field-errors?document_type=all&limit=10"
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {len(data)} error types")
        if data:
            print(f"Top errors:")
            for error in data[:5]:
                print(f"  {error}")
        assert response.status_code == 200
    
    print("✓ Field errors retrieved")


async def test_latency_trend():
    """Test latency trend"""
    print("\n" + "="*60)
    print("Testing: GET /analytics/latency-trend?days=7")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/analytics/latency-trend?days=7")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {len(data)} hourly data points")
        if data:
            print(f"Sample (first 3):")
            for item in data[:3]:
                print(f"  {item}")
        assert response.status_code == 200
    
    print("✓ Latency trend retrieved")


async def test_two_stage_extraction():
    """Test two-stage extraction logging"""
    print("\n" + "="*60)
    print("Testing: Two-stage extraction with OCR correction")
    print("="*60)
    
    extraction_data = {
        "document_type": "invoice",
        "model_used": "two_stage",
        "field_f1_score": 0.94,
        "doc_accuracy": True,
        "latency_ms": 285,
        "stage1_latency_ms": 135,
        "stage2_latency_ms": 150,
        "confidence_score": 0.91,
        "ocr_errors_corrected": 2,
        "file_size_kb": 456,
        "scan_quality": "noisy"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/extractions",
            json=extraction_data
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Two-stage extraction created:")
        print(f"  ID: {data['id']}")
        print(f"  Stage 1 latency: {data['stage1_latency_ms']}ms")
        print(f"  Stage 2 latency: {data['stage2_latency_ms']}ms")
        print(f"  Total latency: {data['latency_ms']}ms")
        print(f"  OCR errors corrected: {data['ocr_errors_corrected']}")
        assert response.status_code == 201
    
    print("✓ Two-stage extraction logged")


async def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*60)
    print("BharatDoc Analytics - API Test Suite")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    
    try:
        # Test health first
        await test_health()
        
        # Test extraction creation
        extraction_id = await test_create_extraction()
        
        # Test field errors
        await test_create_field_errors(extraction_id)
        
        # Test two-stage extraction
        await test_two_stage_extraction()
        
        # Test analytics endpoints
        await test_analytics_overview()
        await test_daily_stats()
        await test_model_comparison()
        await test_field_errors()
        await test_latency_trend()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
