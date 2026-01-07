"""
Configuration management using pydantic-settings.
Loads environment variables and provides typed settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Provider Configuration
    llm_provider: Literal["openai", "anthropic", "google"] = Field(
        default="openai",
        description="LLM provider to use"
    )
    llm_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Model name/ID"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature"
    )

    # API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None

    # Embeddings
    embedding_provider: Literal["openai", "anthropic", "google"] = Field(
        default="openai",
        description="Embedding provider"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name"
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/agent.db",
        description="Database connection URL"
    )
    chroma_persist_dir: str = Field(
        default="./data/chroma",
        description="ChromaDB persistence directory"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="API workers")

    # RAG Configuration
    rag_chunk_size: int = Field(
        default=600,
        description="Token size for document chunks"
    )
    rag_chunk_overlap: int = Field(
        default=100,
        description="Overlap between chunks"
    )
    rag_top_k: int = Field(
        default=8,
        description="Number of chunks to retrieve"
    )
    rag_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for retrieval"
    )

    # Decision Engine Thresholds
    confidence_high_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="High confidence threshold"
    )
    confidence_low_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Low confidence threshold"
    )

    # Tool Configuration
    sendgrid_api_key: str | None = None
    sendgrid_from_email: str | None = None
    google_calendar_credentials_path: str | None = None
    hubspot_api_key: str | None = None
    hubspot_base_url: str = Field(
        default="https://api.hubapi.com",
        description="HubSpot API base URL"
    )

    # Observability
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: str = Field(
        default="./data/logs/agent.log",
        description="Log file path"
    )
    enable_trace_logging: bool = Field(
        default=True,
        description="Enable detailed trace logging"
    )

    # Job Scheduler
    enable_background_jobs: bool = Field(
        default=True,
        description="Enable background job scheduler"
    )
    followup_check_interval_minutes: int = Field(
        default=30,
        description="Interval for checking follow-ups"
    )

    def validate_api_keys(self) -> None:
        """Validate that required API keys are present based on provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required when LLM_PROVIDER=openai")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required when LLM_PROVIDER=anthropic")
        elif self.llm_provider == "google" and not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY required when LLM_PROVIDER=google")

        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required when EMBEDDING_PROVIDER=openai")


# Global settings instance
settings = Settings()
