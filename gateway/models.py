"""Pydantic models for CATS Gateway API requests and responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# --- Request Models ---

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8192, description="User prompt for LLM inference")
    request_tag: str = Field("default", description="Routing hint: 'default', 'fast_ok', or 'high_quality'")


class QualitySampleRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8192)


# --- Response Models ---

class RouteInfo(BaseModel):
    site: str = Field(..., description="Selected inference site: 'cloud' or 'edge'")
    model: str = Field(..., description="Model used for inference")
    strategy: str = Field(..., description="Routing strategy applied")
    total_inference_ms: int = Field(..., description="Total inference time in milliseconds")


class ChatResponse(BaseModel):
    response: str | None = Field(None, description="LLM generated response")
    route: RouteInfo


class QualitySampleResponse(BaseModel):
    prompt: str
    cloud_response: str | None = None
    edge_response: str | None = None
    cloud_model: str = ""
    edge_model: str = ""
    cloud_total_inference_ms: int = 0
    edge_total_inference_ms: int = 0


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, bool]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# --- Generic API Envelope ---

class APIResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
