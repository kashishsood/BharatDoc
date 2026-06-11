"""
FastAPI application for CrewAI-based document processing.

This service provides endpoints for processing Indian documents using
a multi-agent CrewAI system.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from crew import create_document_crew


# Initialize FastAPI app
app = FastAPI(
    title="BharatDoc CrewAI Agent",
    description="Multi-agent document processing system for Indian documents",
    version="1.0.0"
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize the crew
document_crew = create_document_crew()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dictionary with status indicator
    """
    return {"status": "ok"}


@app.post("/process")
async def process_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Process a document image through the CrewAI multi-agent system.
    
    This endpoint accepts an image file, saves it temporarily, and runs
    it through a three-agent crew:
    1. DocumentClassifier: Identifies document type
    2. FieldExtractor: Extracts structured fields
    3. SchemaValidator: Validates against Indian document schemas
    
    Args:
        file: Uploaded image file (JPEG, PNG, PDF)
        
    Returns:
        Dictionary containing processing results from all three agents
        
    Raises:
        HTTPException: If file processing fails
    """
    # Validate file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file
    file_path = UPLOAD_DIR / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )
    
    # Process through the crew
    try:
        result = document_crew.process_document(str(file_path))
        
        # Clean up the uploaded file
        file_path.unlink(missing_ok=True)
        
        return result
    
    except Exception as e:
        # Clean up on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint with API information.
    
    Returns:
        Dictionary with API details
    """
    return {
        "name": "BharatDoc CrewAI Agent",
        "version": "1.0.0",
        "description": "Multi-agent document processing system",
        "endpoints": {
            "POST /process": "Process a document through the CrewAI system",
            "GET /health": "Health check endpoint"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
