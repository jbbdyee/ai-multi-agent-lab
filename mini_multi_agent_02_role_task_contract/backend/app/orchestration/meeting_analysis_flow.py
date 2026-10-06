"""회의 분석 Agent의 Parallel Workers와 Reviewer Join 흐름입니다."""

import asyncio

from app.agents.registry import get_agent
from app.agents.runtime import run_agent
from app.observability.tracker import RunTracker
from app.schemas.contracts import (
    MeetingAnalysisRequest,
    MeetingAnalysisResult,
    MeetingReviewResult,
    MeetingTaskExtractionResult,
    MeetingWorkflowResult,
    MeetingWorkflowTraceEvent,
)


def _transcript_message(request: MeetingAnalysisRequest) -> str:
    title = f"회의 제목: {request.title}\n" if request.title else ""
    lines = "\n".join(f"[{item.speaker}] {item.content}" for item in request.transcript)
    return f"{title}회의 원문:\n{lines}"


async def run_meeting_analysis_flow(
    request: MeetingAnalysisRequest,
    tracker: RunTracker | None = None,
) -> MeetingWorkflowResult:
    """두 작업 Agent를 병렬 실행하고 검증된 결과만 Reviewer에게 전달합니다."""

    message = _transcript_message(request)
    analysis_run, task_run = await asyncio.gather(
        run_agent(get_agent("meeting_analyst_agent"), message, tracker=tracker),
        run_agent(get_agent("meeting_task_manager_agent"), message, tracker=tracker),
    )
    trace = [
        MeetingWorkflowTraceEvent(step=1, phase="parallel_analysis", task_id="analyze_meeting", status=analysis_run["status"]),
        MeetingWorkflowTraceEvent(step=1, phase="parallel_analysis", task_id="extract_meeting_action_items", status=task_run["status"]),
    ]
    failed_runs = [item for item in (analysis_run, task_run) if item["status"] != "completed"]
    if failed_runs:
        return MeetingWorkflowResult(
            status="failed",
            failed_agent_ids=[str(item["agent_id"]) for item in failed_runs],
            failures=failed_runs,
            trace=trace,
        )

    meeting_analysis = MeetingAnalysisResult.model_validate(analysis_run["result"])
    task_extraction = MeetingTaskExtractionResult.model_validate(task_run["result"])
    if tracker:
        tracker.advance(
            "orchestrator",
            "parallel_results_joined",
            "두 분석 Agent의 검증된 결과를 Reviewer Context로 Join했습니다.",
        )
    reviewer_context = {
        "meeting_analysis": meeting_analysis.model_dump(),
        "task_extraction": task_extraction.model_dump(),
    }
    review_run = await run_agent(
        get_agent("meeting_reviewer_agent"), message, reviewer_context, tracker
    )
    trace.append(MeetingWorkflowTraceEvent(step=2, phase="review_join", task_id="review_meeting_results", status=review_run["status"]))
    if review_run["status"] != "completed":
        return MeetingWorkflowResult(
            status="failed",
            meeting_analysis=meeting_analysis,
            task_extraction=task_extraction,
            failed_agent_ids=["meeting_reviewer_agent"],
            failures=[review_run],
            trace=trace,
        )

    review = MeetingReviewResult.model_validate(review_run["result"])
    needs_user_input = any(item.status == "needs_confirmation" for item in task_extraction.action_items)
    status = "review_failed" if review.status == "FAIL" else "needs_user_input" if needs_user_input else "completed"
    return MeetingWorkflowResult(
        status=status,
        meeting_analysis=meeting_analysis,
        task_extraction=task_extraction,
        review=review,
        trace=trace,
    )


async def execute_meeting_tracked(
    run_id: str,
    request: MeetingAnalysisRequest,
) -> None:
    """회의 Workflow를 Background에서 실행하고 Redis Snapshot에 기록합니다."""

    tracker = RunTracker(run_id, total_steps=7)
    tracker.start("회의 분석을 준비하고 있습니다.")
    try:
        result = await run_meeting_analysis_flow(request, tracker)
        payload = result.model_dump(mode="json")
        payload["run_id"] = run_id
        if result.status in {"completed", "needs_user_input", "review_failed"}:
            tracker.finish(payload)
        else:
            tracker.fail("회의 분석의 필수 Agent 또는 계약 검증이 실패했습니다.", payload)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
