"""
Event-driven asynchronous document processing queue.

In production this would be replaced with AWS SQS or Redis Queue (rq).
This implementation demonstrates the event-driven pattern: producers enqueue jobs,
consumers process them asynchronously, event handlers fire on state transitions.

This allows for:
- Non-blocking document uploads (immediate response to client)
- Asynchronous processing (long-running tasks don't block API)
- Event-driven architecture (analytics, notifications, webhooks can subscribe)
- Horizontal scalability (multiple workers can process the same queue)
"""

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable, Optional


@dataclass
class DocumentJob:
    """
    Represents a document processing job in the queue.
    
    Attributes:
        job_id: Unique identifier for the job
        image_path: Path to the uploaded document image
        document_type: Type of document (aadhaar, invoice, etc.) or None if not yet classified
        status: Current status (queued, processing, complete, failed)
        created_at: Timestamp when job was created
        result: Processing result dictionary (None until complete)
        error: Error message if job failed (None if successful)
    """
    job_id: str
    image_path: str
    document_type: Optional[str] = None
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary representation.
        
        Returns:
            Dictionary with all job fields
        """
        return {
            "job_id": self.job_id,
            "image_path": self.image_path,
            "document_type": self.document_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "result": self.result,
            "error": self.error
        }


# Type alias for event handlers
EventHandler = Callable[[str, DocumentJob], Awaitable[None]]


class DocumentQueue:
    """
    Asynchronous event-driven document processing queue.
    
    This queue manages document processing jobs with the following features:
    - FIFO ordering (first in, first out)
    - Event-driven architecture (handlers can subscribe to events)
    - Non-blocking enqueue (returns immediately)
    - Asynchronous processing (background task)
    - Status tracking (by job_id lookup)
    
    Events emitted:
    - job_queued: When a job is added to the queue
    - job_started: When processing begins
    - job_complete: When processing succeeds
    - job_failed: When processing fails
    """
    
    def __init__(self):
        """Initialize the document queue with empty state."""
        self._queue: deque[DocumentJob] = deque()
        self._jobs: Dict[str, DocumentJob] = {}
        self._handlers: Dict[str, list[EventHandler]] = {
            "job_queued": [],
            "job_started": [],
            "job_complete": [],
            "job_failed": []
        }
        self._processing: bool = False
        self._process_task: Optional[asyncio.Task] = None
    
    def on_event(self, event: str, handler: EventHandler) -> None:
        """
        Register an event handler for a specific event type.
        
        Args:
            event: Event name (job_queued, job_started, job_complete, job_failed)
            handler: Async function to call when event occurs
            
        Raises:
            ValueError: If event type is not recognized
        """
        if event not in self._handlers:
            raise ValueError(
                f"Unknown event type: {event}. "
                f"Valid events: {', '.join(self._handlers.keys())}"
            )
        self._handlers[event].append(handler)
    
    async def _emit(self, event: str, job: DocumentJob) -> None:
        """
        Emit an event to all registered handlers.
        
        This method calls all handlers registered for the given event type.
        Handlers are called concurrently using asyncio.gather.
        
        Args:
            event: Event name to emit
            job: Job associated with the event
        """
        if event not in self._handlers:
            return
        
        handlers = self._handlers[event]
        if handlers:
            # Call all handlers concurrently
            await asyncio.gather(
                *[handler(event, job) for handler in handlers],
                return_exceptions=True  # Don't let handler errors break the queue
            )
    
    async def enqueue(self, job: DocumentJob) -> str:
        """
        Add a job to the processing queue.
        
        This method:
        1. Adds the job to the internal queue
        2. Stores the job for status lookup
        3. Emits a job_queued event
        4. Starts the processing task if not already running
        
        Args:
            job: DocumentJob to enqueue
            
        Returns:
            Job ID for status tracking
        """
        # Add to queue and job registry
        self._queue.append(job)
        self._jobs[job.job_id] = job
        
        # Emit queued event
        await self._emit("job_queued", job)
        
        # Start processing if not already running
        if not self._processing:
            self._process_task = asyncio.create_task(self._process_queue())
        
        return job.job_id
    
    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a job.
        
        Args:
            job_id: Unique identifier for the job
            
        Returns:
            Dictionary with job details, or None if job not found
        """
        job = self._jobs.get(job_id)
        if job:
            return job.to_dict()
        return None
    
    async def _process_queue(self) -> None:
        """
        Background task that processes jobs from the queue.
        
        This method:
        1. Continuously processes jobs while queue is not empty
        2. Updates job status (queued → processing → complete/failed)
        3. Emits events at each state transition
        4. Handles errors gracefully
        
        In production, this would be replaced by:
        - AWS SQS worker polling messages
        - Redis Queue (rq) worker consuming jobs
        - Celery worker executing tasks
        """
        self._processing = True
        
        try:
            while self._queue:
                # Get next job
                job = self._queue.popleft()
                
                # Update status to processing
                job.status = "processing"
                await self._emit("job_started", job)
                
                try:
                    # Simulate document processing
                    # In production, this would call:
                    # - CLIP classifier for document type
                    # - Donut/LayoutLM for field extraction
                    # - Schema validator for validation
                    result = await self._process_document(job)
                    
                    # Update job with success
                    job.status = "complete"
                    job.result = result
                    await self._emit("job_complete", job)
                
                except Exception as e:
                    # Update job with failure
                    job.status = "failed"
                    job.error = str(e)
                    await self._emit("job_failed", job)
        
        finally:
            self._processing = False
    
    async def _process_document(self, job: DocumentJob) -> Dict[str, Any]:
        """
        Process a single document job.
        
        This is a mock implementation. In production, this would:
        1. Load the image from job.image_path
        2. Call the CLIP classifier to get document_type
        3. Route to appropriate model (Donut/LayoutLM/TrOCR)
        4. Extract structured fields
        5. Validate against schema
        6. Return extraction result
        
        Args:
            job: DocumentJob to process
            
        Returns:
            Dictionary with extraction results
            
        Raises:
            Exception: If processing fails
        """
        # Simulate processing delay
        await asyncio.sleep(2)
        
        # Mock classification based on filename
        image_lower = job.image_path.lower()
        if "aadhaar" in image_lower:
            job.document_type = "aadhaar"
            result = {
                "document_type": "aadhaar",
                "fields": {
                    "aadhaar_number": "1234 5678 9012",
                    "name": "Rajesh Kumar",
                    "dob": "15/08/1990",
                    "gender": "Male"
                },
                "confidence": 0.95,
                "processing_time_ms": 1850
            }
        elif "invoice" in image_lower or "gst" in image_lower:
            job.document_type = "invoice"
            result = {
                "document_type": "invoice",
                "fields": {
                    "invoice_number": "INV-2024-001",
                    "gstin": "29ABCDE1234F1Z5",
                    "total_amount": "₹15,750.00",
                    "date": "15/01/2024"
                },
                "confidence": 0.92,
                "processing_time_ms": 2100
            }
        elif "lic" in image_lower or "policy" in image_lower:
            job.document_type = "lic_policy"
            result = {
                "document_type": "lic_policy",
                "fields": {
                    "policy_number": "LIC-789456123",
                    "policy_holder_name": "Priya Sharma",
                    "sum_assured": "₹10,00,000",
                    "premium_amount": "₹15,000"
                },
                "confidence": 0.89,
                "processing_time_ms": 1950
            }
        else:
            job.document_type = "unknown"
            result = {
                "document_type": "unknown",
                "fields": {},
                "confidence": 0.50,
                "processing_time_ms": 1500
            }
        
        return result
    
    def get_queue_size(self) -> int:
        """
        Get the current number of jobs in the queue.
        
        Returns:
            Number of jobs waiting to be processed
        """
        return len(self._queue)
    
    def get_total_jobs(self) -> int:
        """
        Get the total number of jobs tracked (queued + processing + complete + failed).
        
        Returns:
            Total number of jobs in the system
        """
        return len(self._jobs)
