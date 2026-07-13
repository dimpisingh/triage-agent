from typing import Optional
from pydantic import BaseModel, Field


class BuildFailureEvent(BaseModel):
    """Mirrors the Kafka message schema from the Java producer."""

    eventId: str
    repo: str
    branch: Optional[str] = None
    commitSha: Optional[str] = None
    pipelineId: Optional[str] = None
    stage: Optional[str] = "build"
    failureType: str
    exitCode: Optional[int] = 1
    rawLogExcerpt: str
    logStorageUrl: Optional[str] = None
    affectedModule: Optional[str] = None
    triggeredBy: Optional[str] = None
    retryCount: int = 0


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    score: float


class Diagnosis(BaseModel):
    root_cause: str
    proposed_fix: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = []
    escalated: bool = False
    escalation_reason: Optional[str] = None


class DiagnoseResponse(BaseModel):
    eventId: str
    diagnosis: Diagnosis
    retrieved_chunks: list[RetrievedChunk]
