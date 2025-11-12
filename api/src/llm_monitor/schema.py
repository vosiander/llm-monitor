from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ModelDetails(BaseModel):
    parent_model: str
    format: str
    family: str
    families: list[str]
    parameter_size: str
    quantization_level: str


class Model(BaseModel):
    name: str
    model: str
    size: int
    digest: str
    details: ModelDetails
    expires_at: str
    size_vram: int


class ProcessStatus(BaseModel):
    models: list[Model]
    is_online: bool
    ip: str = ""
    port: int = 11434


class DiscoveredHost(BaseModel):
    """Represents a discovered Ollama host on the network"""
    ip: str
    port: int = 11434
    hostname: Optional[str] = None
    last_seen: datetime
    is_online: bool = True
    
    @property
    def url(self) -> str:
        """Compute the URL for this host"""
        return f"http://{self.ip}:{self.port}"


class DiscoveryConfig(BaseModel):
    """Configuration for network discovery from environment variables"""
    cidr_ranges: list[str] = Field(description="CIDR ranges to scan, e.g., ['192.168.1.0/24']")
    interval_seconds: int = Field(default=60, description="Discovery interval in seconds")
    max_parallel: int = Field(default=10, description="Maximum parallel connections")
    timeout_seconds: float = Field(default=0.5, description="Connection timeout in seconds")
    port: int = Field(default=11434, description="Port to scan for Ollama")


class LiteLLMConfig(BaseModel):
    """Configuration for LiteLLM integration"""
    url: str = Field(description="LiteLLM API base URL")
    master_key: str = Field(description="LiteLLM master API key")


class BulkCreateRequest(BaseModel):
    """Request to create models in LiteLLM for multiple hosts"""
    model_name: str = Field(description="Model name to create in LiteLLM (e.g., 'blablub-gemma3')")
    ollama_model: str = Field(description="Ollama model to use (e.g., 'gemma3' which will be formatted as 'ollama_chat/gemma3')")
    host_labels: list[str] = Field(description="List of host labels to create models for")
