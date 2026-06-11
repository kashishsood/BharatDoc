"""
Analytics client for logging extraction metrics from other services.

This client is designed to never raise exceptions - it logs warnings
instead to ensure it never breaks the main inference pipeline.
"""

import logging
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """
    Non-blocking analytics client.
    
    All methods catch exceptions and return None on failure
    to ensure analytics never breaks the main pipeline.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize analytics client.
        
        Args:
            base_url: Base URL of analytics service (e.g., http://localhost:8002)
        """
        self.base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def log_extraction(self, data: Dict) -> Optional[str]:
        """
        Log an extraction to analytics service.
        
        Args:
            data: Dictionary with extraction log data matching ExtractionLogCreate schema
        
        Returns:
            Extraction ID string if successful, None if analytics service is down
            
        This method never raises - it catches all exceptions and logs warnings.
        """
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/extractions",
                json=data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    extraction_id = result.get('id')
                    logger.info(f"Logged extraction to analytics: {extraction_id}")
                    return extraction_id
                else:
                    logger.warning(
                        f"Analytics service returned status {response.status} "
                        f"for extraction log"
                    )
                    return None
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Failed to connect to analytics service: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error logging extraction to analytics: {e}")
            return None
    
    async def log_field_errors(
        self,
        extraction_id: str,
        errors: List[Dict]
    ) -> None:
        """
        Log field-level errors for an extraction.
        
        Args:
            extraction_id: UUID of the extraction log
            errors: List of dictionaries with field error data
        
        This method never raises - it catches all exceptions and logs warnings.
        """
        if not errors:
            return
        
        try:
            session = await self._get_session()
            
            async with session.post(
                f"{self.base_url}/extractions/{extraction_id}/errors",
                json=errors
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    count = result.get('inserted', 0)
                    logger.info(
                        f"Logged {count} field errors to analytics "
                        f"for extraction {extraction_id}"
                    )
                else:
                    logger.warning(
                        f"Analytics service returned status {response.status} "
                        f"for field errors"
                    )
                    
        except aiohttp.ClientError as e:
            logger.warning(
                f"Failed to connect to analytics service for field errors: {e}"
            )
        except Exception as e:
            logger.warning(
                f"Unexpected error logging field errors to analytics: {e}"
            )
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Analytics client session closed")
