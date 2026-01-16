"""
Gender Inclusion Tracker - Configuration Module
Handles environment variables and application settings.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    data_gov_api_key: str = Field(default="", env="DATA_GOV_API_KEY")
    api1_base: str = Field(default="https://api.data.gov.in/resource", env="API1_BASE")
    api2_base: str = Field(default="https://api.data.gov.in/resource", env="API2_BASE")
    api3_base: str = Field(default="https://api.data.gov.in/resource", env="API3_BASE")
    
    # Resource IDs
    enrolment_resource_id: str = Field(
        default="ecd49b12-3084-4521-8f7e-ca8bf72069ba",
        env="ENROLMENT_RESOURCE_ID"
    )
    demographic_resource_id: str = Field(
        default="19eac040-0b94-49fa-b239-4f2fd8677d53",
        env="DEMOGRAPHIC_RESOURCE_ID"
    )
    biometric_resource_id: str = Field(
        default="65454dab-1517-40a3-ac1d-47d4dfe6891c",
        env="BIOMETRIC_RESOURCE_ID"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # ML Configuration
    default_risk_threshold: float = Field(default=0.85, env="DEFAULT_RISK_THRESHOLD")
    random_seed: int = Field(default=42, env="RANDOM_SEED")
    
    # Security
    api_token_secret: str = Field(default="dev-secret-change-in-prod", env="API_TOKEN_SECRET")
    enable_privacy_noise: bool = Field(default=False, env="ENABLE_PRIVACY_NOISE")
    noise_epsilon: float = Field(default=0.1, env="NOISE_EPSILON")
    
    # Storage Paths
    artifacts_dir: Path = Field(default=Path("./artifacts"), env="ARTIFACTS_DIR")
    models_dir: Path = Field(default=Path("./models"), env="MODELS_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
