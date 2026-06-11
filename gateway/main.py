"""
BharatDoc-VLM: API Gateway with Event-Driven Queue
====================================================

Extended gateway with asynchronous job queue for document processing.
This version demonstrates event-driven architecture with non-blocking uploads.

New endpoints:
- POST /documents/process: Upload document, get immediate job_id response
- GET /documents/{job_id}/status: Check job status and get results
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import the original gateway functionality
from gateway import create_app as create_base_app

# Import the queue system
from queue import DocumentQueue, DocumentJob

logger = logging.getLogger(__name__)

# =============================================================
# Global Queue Instance
# =============================================================

document_queue = DocumentQueue()


# =============================================================
# Event Handlers
# =============================================================

async def analytics_event_handler(event: str, job: DocumentJob) -> None:
    """
    Analytics event handler that logs completed jobs.
    
    This handler is called when a job completes successfully.
    In production, this would:
    - Send metrics to analytics service
    - Update dashboards
    - Trigger notifications
    - Send webhooks to external systems
    
    Args:
        event: Event name (should be 'job_complete')
        job: The completed document job
    """
    if event == "job_complete":
        logger.info(
            f"📊 Analytics: Job {job.job_id} completed | "
            f"doc_type={job.document_type} | "
            f"processing_time={(job.result or {}).get('processing_time_ms', 'N/A')}ms"
        )
        # In production:
        # await analytics_client.log_extraction(
        #     document_type=job.document_type,
        #     fields_extracted=list(job.result.get('fields', {}).keys()),
        #     confidence=job.result.get('confidence'),
        #     latency_ms=job.result.get('processing_time_ms')
        # )


async def notification_event_handler(event: str, job: DocumentJob) -> None:
    """
    Notification event handler for job failures.
    
    Sends alerts when jobs fail so they can be investigated.
    
    Args:
        event: Event name (should be 'job_failed')
        job: The failed document job
    """
    if event == "job_failed":
        logger.error(
            f"🚨 Alert: Job {job.job_id} FAILED | "
            f"error={job.error} | "
            f"image_path={job.image_path}"
        )
        # In production:
        # await notification_service.send_alert(
        #     title=f"Document Processing Failed",
        #     message=f"Job {job.job_id} failed: {job.error}",
        #     severity="error"
        # )


# =============================================================
# FastAPI Application
# =============================================================

def create_app_with_queue(use_mock: bool = True) -> FastAPI:
    """
    Create the gateway FastAPI application with queue support.
    
    Args:
        use_mock: Use mock classifier and router (no real models needed)
        
    Returns:
        FastAPI application with queue endpoints
    """
    # Get the base app with original endpoints
    app = create_base_app(use_mock=use_mock)
    
    # Update app metadata
    app.title = "BharatDoc-VLM Gateway with Queue"
    app.description = "Document intelligence gateway with async job queue"
    
    # Register event handlers
    document_queue.on_event("job_complete", analytics_event_handler)
    document_queue.on_event("job_failed", notification_event_handler)
    
    @app.post("/documents/process")
    async def process_document_async(
        file: UploadFile = File(..., description="Document image to process")
    ) -> Dict[str, Any]:
        """
        Upload a document for asynchronous processing.
        
        This endpoint:
        1. Saves the uploaded file
        2. Creates a DocumentJob
        3. Enqueues it for processing
        4. Returns immediately with job_id (non-blocking)
        
        The client can then poll /documents/{job_id}/status to check progress.
        
        Args:
            file: Uploaded document image file
            
        Returns:
            Dictionary with job_id and initial status
            
        Raises:
            HTTPException: If file upload fails
        """
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        job_id = str(uuid.uuid4())
        file_path = upload_dir / f"{job_id}{file_ext}"
        
        try:
            content = await file.read()
            with file_path.open("wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Create job
        job = DocumentJob(
            job_id=job_id,
            image_path=str(file_path),
            status="queued"
        )
        
        # Enqueue for processing
        await document_queue.enqueue(job)
        
        logger.info(
            f"✅ Job {job_id} enqueued | "
            f"filename={file.filename} | "
            f"queue_size={document_queue.get_queue_size()}"
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Document uploaded successfully. Use job_id to check status.",
            "status_endpoint": f"/documents/{job_id}/status"
        }
    
    @app.get("/documents/{job_id}/status")
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """
        Get the current status of a document processing job.
        
        Status values:
        - queued: Job is waiting to be processed
        - processing: Job is currently being processed
        - complete: Job finished successfully (result available)
        - failed: Job failed (error message available)
        
        Args:
            job_id: Unique identifier for the job
            
        Returns:
            Dictionary with job status and details
            
        Raises:
            HTTPException: If job_id not found
        """
        status = await document_queue.get_status(job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        return status
    
    @app.get("/queue/stats")
    async def get_queue_stats() -> Dict[str, Any]:
        """
        Get statistics about the job queue.
        
        Returns:
            Dictionary with queue metrics
        """
        return {
            "queue_size": document_queue.get_queue_size(),
            "total_jobs": document_queue.get_total_jobs(),
            "is_processing": document_queue._processing
        }
    
    return app


# =============================================================
# Entrypoint
# =============================================================

app = create_app_with_queue(use_mock=True)

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="BharatDoc-VLM Gateway with Queue")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock models")
    parser.add_argument("--no-mock", dest="mock", action="store_false", help="Use real models")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    app = create_app_with_queue(use_mock=args.mock)
    uvicorn.run(app, host=args.host, port=args.port)
