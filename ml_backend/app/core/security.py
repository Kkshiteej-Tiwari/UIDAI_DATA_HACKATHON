"""
Gender Inclusion Tracker - Security Utilities
Handles API authentication and data privacy.
"""

import hashlib
import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import numpy as np

from .config import settings


# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify API key for protected endpoints."""
    if settings.debug:
        # In debug mode, allow requests without API key
        return "debug-user"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # Simple token verification (in production, use proper JWT or OAuth)
    if not secrets.compare_digest(api_key, settings.api_token_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key


def anonymize_id(identifier: str) -> str:
    """
    Hash an identifier to anonymize it.
    Used for PII protection in outputs.
    """
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]


def add_differential_privacy_noise(
    value: float,
    epsilon: float = None,
    sensitivity: float = 1.0
) -> float:
    """
    Add Laplacian noise for differential privacy.
    
    Args:
        value: Original value
        epsilon: Privacy parameter (lower = more privacy)
        sensitivity: Query sensitivity
    
    Returns:
        Noisy value
    """
    if not settings.enable_privacy_noise:
        return value
    
    epsilon = epsilon or settings.noise_epsilon
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    return value + noise


def sanitize_output_for_public(data: dict) -> dict:
    """
    Sanitize output data for public release.
    Removes or rounds sensitive values.
    """
    sanitized = data.copy()
    
    # Round percentages to avoid re-identification
    for key in ['female_coverage_ratio', 'male_coverage_ratio']:
        if key in sanitized:
            sanitized[key] = round(sanitized[key], 2)
    
    # Remove exact counts if privacy is enabled
    if settings.enable_privacy_noise:
        for key in ['male_enrolled', 'female_enrolled', 'total_enrolled']:
            if key in sanitized:
                sanitized[key] = add_differential_privacy_noise(sanitized[key])
    
    return sanitized
