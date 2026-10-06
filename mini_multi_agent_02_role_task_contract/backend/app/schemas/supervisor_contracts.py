from typing import Literal

from pydantic import BaseModel, Field


WorkerId = Literal[
    "meeting_analyst_agent",
    "meeting_task_manager_agent",
    "meeting_reviewer_agent",
]
WorkerProvider = Literal["openai", "gemini", "ollama", "gemma"]


class WorkerDefinition(BaseModel):
    name: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    provider: WorkerProvider
    output_contract: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)


class WorkerDefinitions(BaseModel):
    workers: dict[WorkerId, WorkerDefinition] = Field(min_length=1)


class SupervisorDecision(BaseModel):
    agent_id: Literal["meeting_supervisor_agent"] = "meeting_supervisor_agent"
    next_worker: Literal[
        "meeting_analyst_agent",
        "meeting_task_manager_agent",
        "meeting_reviewer_agent",
        "finish",
        "needs_user_input",
    ]
    reason: str = Field(min_length=1)


class SupervisorTraceEvent(BaseModel):
    step: int = Field(ge=1)
    actor: str
    action: str
    detail: str


class MeetingSupervisorResult(BaseModel):
    status: Literal["completed", "needs_user_input", "failed"]
    meeting_analysis: dict[str, object] | None = None
    task_extraction: dict[str, object] | None = None
    review: dict[str, object] | None = None
    completed_workers: list[WorkerId] = Field(default_factory=list)
    retry_counts: dict[str, int] = Field(default_factory=dict)
    trace: list[SupervisorTraceEvent] = Field(default_factory=list)
    error: str | None = None
