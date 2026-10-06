"""Tool 없이 LLM Supervisor와 LLM Worker만 사용하는 회의 Routing 실습입니다."""

import json

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.schemas.contracts import (
    MeetingAnalysisRequest,
    MeetingAnalysisResult,
    MeetingReviewResult,
    MeetingTaskExtractionResult,
)
from app.schemas.supervisor_contracts import (
    MeetingSupervisorResult,
    SupervisorDecision,
    SupervisorTraceEvent,
    WorkerDefinition,
)
from app.services.worker_definition_service import load_worker_definitions


MAX_STEPS = 8
MAX_RETRIES_PER_WORKER = 1
WORKER_CONTEXTS = {
    "meeting_analyst_agent": ("transcript",),
    "meeting_task_manager_agent": ("transcript",),
    "meeting_reviewer_agent": ("transcript", "meeting_analysis", "task_extraction"),
}


def _transcript_message(request: MeetingAnalysisRequest) -> str:
    title = f"회의 제목: {request.title}\n" if request.title else ""
    transcript = "\n".join(
        f"[{segment.speaker}] {segment.content}" for segment in request.transcript
    )
    return f"{title}회의 원문:\n{transcript}"


def _has_missing_action_information(task_extraction: dict[str, object] | None) -> bool:
    if not task_extraction:
        return False
    return any(
        item.get("status") == "needs_confirmation"
        for item in task_extraction.get("action_items", [])
    )


def _available_context(
    request: MeetingAnalysisRequest,
    meeting_analysis: dict[str, object] | None,
    task_extraction: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "transcript": [item.model_dump() for item in request.transcript],
        "meeting_analysis": meeting_analysis,
        "task_extraction": task_extraction,
    }


def _minimum_context(
    worker_id: str,
    context: dict[str, object],
) -> dict[str, object]:
    required_context = WORKER_CONTEXTS[worker_id]
    missing = [name for name in required_context if context.get(name) is None]
    if missing:
        raise ValueError(
            f"{worker_id} 실행에 필요한 Context가 없습니다: {', '.join(missing)}"
        )
    return {name: context[name] for name in required_context}


def _validate_decision(
    decision: SupervisorDecision,
    workers: dict[str, WorkerDefinition],
    meeting_analysis: dict[str, object] | None,
    task_extraction: dict[str, object] | None,
    review: dict[str, object] | None,
) -> None:
    selected = decision.next_worker
    if selected in workers:
        return
    if selected == "finish":
        if not review or review.get("status") != "PASS":
            raise ValueError("Reviewer PASS 전에는 finish할 수 없습니다.")
        if _has_missing_action_information(task_extraction):
            raise ValueError("확인이 필요한 Action Item이 있으면 finish할 수 없습니다.")
        return
    if selected == "needs_user_input":
        if not _has_missing_action_information(task_extraction):
            raise ValueError("누락 정보가 없으면 needs_user_input을 선택할 수 없습니다.")
        return
    raise ValueError(f"허용되지 않은 Supervisor 결정입니다: {selected}")


async def run_supervisor_meeting_flow(
    request: MeetingAnalysisRequest,
    *,
    max_steps: int = MAX_STEPS,
) -> MeetingSupervisorResult:
    workers = load_worker_definitions()
    message = _transcript_message(request)
    meeting_analysis: dict[str, object] | None = None
    task_extraction: dict[str, object] | None = None
    review: dict[str, object] | None = None
    completed_workers: list[str] = []
    retry_counts: dict[str, int] = {}
    trace: list[SupervisorTraceEvent] = []

    for step in range(1, max_steps + 1):
        supervisor_context = {
            "workers": {
                worker_id: worker.model_dump()
                for worker_id, worker in workers.items()
            },
            "state": {
                "meeting_analysis": meeting_analysis,
                "task_extraction": task_extraction,
                "review": review,
                "completed_workers": completed_workers,
                "retry_counts": retry_counts,
                "has_missing_action_information": _has_missing_action_information(task_extraction),
            },
        }
        supervisor_run = await run_agent(
            get_agent("meeting_supervisor_agent"),
            message,
            supervisor_context,
        )
        if supervisor_run["result"] is None:
            return MeetingSupervisorResult(
                status="failed",
                meeting_analysis=meeting_analysis,
                task_extraction=task_extraction,
                review=review,
                completed_workers=completed_workers,
                retry_counts=retry_counts,
                trace=trace,
                error=str(supervisor_run.get("error") or "Supervisor 실행 실패"),
            )

        decision = SupervisorDecision.model_validate(supervisor_run["result"])
        trace.append(SupervisorTraceEvent(
            step=step,
            actor="meeting_supervisor_agent",
            action=f"route:{decision.next_worker}",
            detail=decision.reason,
        ))
        try:
            _validate_decision(
                decision, workers, meeting_analysis, task_extraction, review
            )
        except ValueError as error:
            return MeetingSupervisorResult(
                status="failed",
                meeting_analysis=meeting_analysis,
                task_extraction=task_extraction,
                review=review,
                completed_workers=completed_workers,
                retry_counts=retry_counts,
                trace=trace,
                error=str(error),
            )

        if decision.next_worker == "finish":
            return MeetingSupervisorResult(
                status="completed",
                meeting_analysis=meeting_analysis,
                task_extraction=task_extraction,
                review=review,
                completed_workers=completed_workers,
                retry_counts=retry_counts,
                trace=trace,
            )
        if decision.next_worker == "needs_user_input":
            return MeetingSupervisorResult(
                status="needs_user_input",
                meeting_analysis=meeting_analysis,
                task_extraction=task_extraction,
                review=review,
                completed_workers=completed_workers,
                retry_counts=retry_counts,
                trace=trace,
            )

        worker = workers[decision.next_worker]
        worker_id = decision.next_worker
        context = _available_context(request, meeting_analysis, task_extraction)
        worker_context = _minimum_context(worker_id, context)
        attempts = retry_counts.get(worker_id, 0)
        if worker_id in completed_workers:
            if attempts >= MAX_RETRIES_PER_WORKER:
                return MeetingSupervisorResult(
                    status="failed",
                    meeting_analysis=meeting_analysis,
                    task_extraction=task_extraction,
                    review=review,
                    completed_workers=completed_workers,
                    retry_counts=retry_counts,
                    trace=trace,
                    error=f"{worker_id} 최대 재실행 횟수를 초과했습니다.",
                )
            retry_counts[worker_id] = attempts + 1

        worker_run = await run_agent(
            get_agent(worker_id),
            message,
            worker_context,
        )
        if worker_run["result"] is None:
            return MeetingSupervisorResult(
                status="failed",
                meeting_analysis=meeting_analysis,
                task_extraction=task_extraction,
                review=review,
                completed_workers=completed_workers,
                retry_counts=retry_counts,
                trace=trace,
                error=str(worker_run.get("error") or f"{worker_id} 실행 실패"),
            )

        if worker_id == "meeting_analyst_agent":
            meeting_analysis = MeetingAnalysisResult.model_validate(worker_run["result"]).model_dump()
            review = None
        elif worker_id == "meeting_task_manager_agent":
            task_extraction = MeetingTaskExtractionResult.model_validate(worker_run["result"]).model_dump()
            review = None
        else:
            review = MeetingReviewResult.model_validate(worker_run["result"]).model_dump()

        if worker_id not in completed_workers:
            completed_workers.append(worker_id)
        trace.append(SupervisorTraceEvent(
            step=step,
            actor=worker_id,
            action="worker_completed",
            detail=json.dumps(worker_context, ensure_ascii=False, default=str),
        ))

    return MeetingSupervisorResult(
        status="failed",
        meeting_analysis=meeting_analysis,
        task_extraction=task_extraction,
        review=review,
        completed_workers=completed_workers,
        retry_counts=retry_counts,
        trace=trace,
        error=f"최대 실행 단계({max_steps})를 초과했습니다.",
    )
