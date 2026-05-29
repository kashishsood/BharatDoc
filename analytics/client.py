"""
BharatDoc Analytics Client
Async HTTP client for logging extraction metrics from the gateway
"""

import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """
    Async HTTP client for the analytics service.
    
    IMPORTANT: This client never raises exceptions. If the analytics service
    is down, it logs a warning and continues. The main inference pipeline
    must never fail because analytics is unavailable.
    """
    
    def __init__(self, base_url: str, timeout: float = 5.0):
        """
        Initialize analytics client
        
        Args:
            base_url: Base URL of analytics service (e.g., http://analytics:8002)
            timeout: Request timeout in seconds (default: 5.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def log_extraction(self, extraction_data: Dict) -> Optional[str]:
        """
        Log an extraction to the analytics service
        
        Args:
            extraction_data: Dictionary with extraction log fields:
                - document_type: str
                - model_used: str
                - field_f1_score: float
                - doc_accuracy: bool
                - latency_ms: int
                - stage1_latency_ms: int (optional)
                - stage2_latency_ms: int (optional)
                - confidence_score: float
                - ocr_errors_corrected: int (optional, default 0)
                - file_size_kb: int
                - scan_quality: str
        
        Returns:
            extraction_id (UUID as string) if successful, None otherwise
        
        Never raises exceptions - logs warnings instead
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/extractions",
                json=extraction_data
            )
            
            if response.status_code == 201:
                data = response.json()
                extraction_id = data.get("id")
                logger.info(f"Logged extraction to analytics: {extraction_id}")
                return extraction_id
            else:
                logger.warning(
                    f"Analytics service returned {response.status_code}: {response.text}"
                )
                return None
        
        except httpx.TimeoutException:
            logger.warning(
                f"Analytics service timeout after {self.timeout}s - continuing without logging"
            )
            return None
        
        except httpx.ConnectError:
            logger.warning(
                "Analytics service unavailable - continuing without logging"
            )
            return None
        
        except Exception as e:
            logger.warning(
                f"Failed to log extraction to analytics: {e} - continuing without logging"
            )
            return None
    
    async def log_field_errors(
        self,
        extraction_id: str,
        errors: List[Dict]
    ) -> bool:
        """
        Log field-level errors for an extraction
        
        Args:
            extraction_id: UUID of the extraction log
            errors: List of error dictionaries with fields:
                - field_name: str
                - expected_value: str (optional)
                - extracted_value: str (optional)
                - error_type: str
                - confidence: float
        
        Returns:
            True if successful, False otherwise
        
        Never raises exceptions - logs warnings instead
        """
        if not errors:
            return True
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/extractions/{extraction_id}/errors",
                json=errors
            )
            
            if response.status_code == 201:
                data = response.json()
                count = data.get("inserted", 0)
                logger.info(
                    f"Logged {count} field errors to analytics for extraction {extraction_id}"
                )
                return True
            else:
                logger.warning(
                    f"Analytics service returned {response.status_code} for field errors: {response.text}"
                )
                return False
        
        except httpx.TimeoutException:
            logger.warning(
                f"Analytics service timeout after {self.timeout}s - field errors not logged"
            )
            return False
        
        except httpx.ConnectError:
            logger.warning(
                "Analytics service unavailable - field errors not logged"
            )
            return False
        
        except Exception as e:
            logger.warning(
                f"Failed to log field errors to analytics: {e}"
            )
            return False
    
    async def health_check(self) -> bool:
        """
        Check if analytics service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
        
        except Exception:
            return False


# Convenience function for one-off usage
async def log_extraction_simple(
    base_url: str,
    extraction_data: Dict
) -> Optional[str]:
    """
    Simple one-off function to log an extraction
    
    Args:
        base_url: Analytics service URL
        extraction_data: Extraction log data
    
    Returns:
        extraction_id if successful, None otherwise
    """
    client = AnalyticsClient(base_url)
    try:
        return await client.log_extraction(extraction_data)
    finally:
        await client.close()
