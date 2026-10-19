"""Typed API contract for the Knowledge Brain. Tasks 2 & 3 depend on THESE shapes only."""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=10)


class Source(BaseModel):
    title: str
    url: str
    section: str = ""
    relevance: float = 0.0
    image_refs: list[str] = []


class QueryResponse(BaseModel):
    answer: str
    status: str  # "answered" | "insufficient_evidence"
    sources: list[Source] = []
    # confidence = top retrieval score normalised to 0-1. It is a RETRIEVAL signal,
    # not a calibrated probability of correctness. Documented as such in DESIGN.md.
    confidence: float = 0.0
    needs_human: bool = False
    escalation_id: str | None = None
    model_mode: str = "extractive-fallback"  # or "claude:<model-id>"


class EscalationCreate(BaseModel):
    question: str
    reason: str = "insufficient_evidence"
    context: str = ""


class EscalationResolve(BaseModel):
    expert_answer: str = Field(min_length=5)
    reviewer: str = "expert"


class IngestionRunRequest(BaseModel):
    sitemap_url: str = "https://support.brilliantdirectories.com/support/sitemap.xml"
    limit: int = Field(default=20, ge=1, le=2000)  # start small, prove politeness, then scale
    delay_seconds: float = Field(default=1.0, ge=0.2, le=10)
