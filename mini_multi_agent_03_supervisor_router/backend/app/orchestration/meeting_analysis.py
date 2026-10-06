"""회의 음성 처리 Supervisor–Worker 오케스트레이션."""

import json

from pydantic import ValidationError

from app.agents.registry import get_agent
from app.agents.runtime import run_profile
from app.schemas.workflow import (
    AudioProcessingResult,
    MeetingActionItemResult,
    MeetingAnalysisResult,
    MeetingReviewResult,
    MeetingSupervisorDecision,
    MeetingWorkflowRequest,
)


MAX_RETRIES_PER_WORKER = 1
MAX_LLM_CALLS = 21
STAGES = [
    ("audio_processing_agent", "audio_processing"),
    ("meeting_analyst_agent", "analysis"),
    ("meeting_action_item_agent", "action_items"),
]
WORKER_SCHEMAS = {
    "audio_processing_agent": AudioProcessingResult,
    "meeting_analyst_agent": MeetingAnalysisResult,
    "meeting_action_item_agent": MeetingActionItemResult,
    "meeting_reviewer_agent": MeetingReviewResult,
}


def expected_next(state: dict[str, object]) -> str:
    if state["pending_retry"] is not None:
        return str(state["pending_retry"])
    for agent_id, field in STAGES:
        if state[field] is None:
            return agent_id
    if state["review_required"] or not state["reviews"]:
        return "meeting_reviewer_agent"
    if state["reviews"][-1]["approved"]:
        return "finish"
    return "needs_attention"


def worker_prompt(agent_id: str, request: MeetingWorkflowRequest, state: dict[str, object]) -> str:
    common = f"음성 ID: {request.audio_id}\n사용자 요청: {request.request}\n"
    if agent_id == "audio_processing_agent":
        return common + (
            "네 개의 Mock Tool 결과를 결합해 음성 메타데이터, 화자 구간, 전사와 참석자 정보를 "
            "AudioProcessingResult로 반환하세요. Tool 결과를 바꾸지 마세요."
        )
    if agent_id == "meeting_analyst_agent":
        return common + (
            f"검증된 음성 처리 Context: {json.dumps(state['audio_processing'], ensure_ascii=False)}\n"
            "전사 근거와 함께 요약, 논점과 결정사항을 MeetingAnalysisResult로 반환하세요."
        )
    if agent_id == "meeting_action_item_agent":
        context = {"audio_processing": state["audio_processing"], "analysis": state["analysis"]}
        return common + (
            f"검증된 Context: {json.dumps(context, ensure_ascii=False)}\n"
            "명시된 Action Item만 MeetingActionItemResult로 반환하세요."
        )

    demonstration = ""
    if request.demonstrate_revision and not any(state["retry_counts"].values()):
        demonstration = (
            "재실행 실습을 위해 첫 검토는 approved=false, target_agent_id=audio_processing_agent, "
            "feedback=['음성 처리 결과를 다시 확인하세요.']로 반환하세요. "
        )
    return common + (
        f"전체 State: {json.dumps(state, ensure_ascii=False)}\n"
        f"검증 Tool 결과: {json.dumps(state.get('validation'), ensure_ascii=False)}\n"
        + demonstration
        + "검증 Tool에 문제가 있으면 해당 target_agent_id를 선택하고, 문제가 없으면 승인하세요."
    )


def tool_inputs(
    agent_id: str,
    request: MeetingWorkflowRequest,
    state: dict[str, object],
) -> dict[str, dict[str, object]]:
    if agent_id == "audio_processing_agent":
        audio_only = {"audio_id": request.audio_id}
        return {
            "get_mock_audio_metadata": audio_only,
            "run_mock_speaker_diarization": audio_only,
            "run_mock_speech_to_text": audio_only,
            "lookup_mock_participants": audio_only,
        }
    if agent_id == "meeting_reviewer_agent":
        audio = state["audio_processing"]
        return {
            "validate_mock_meeting_result": {
                "audio_id": request.audio_id,
                "audio_metadata": audio["audio_metadata"],
                "speaker_segments": audio["speaker_segments"],
                "transcript": audio["transcript"],
                "participants": audio["participants"],
                "analysis": state["analysis"],
                "action_items": state["action_items"],
            }
        }
    return {}


def verify_worker(agent_id: str, response: dict[str, object]):
    payload = response.get("result")
    if payload is None:
        return None, str(response.get("error") or "Worker 결과가 없습니다.")
    try:
        verified = WORKER_SCHEMAS[agent_id].model_validate(payload)
    except ValidationError as error:
        return None, str(error)
    if agent_id == "meeting_reviewer_agent":
        validation = response.get("tool_results", {}).get("validate_mock_meeting_result", {})
        if verified.approved:
            verified.target_agent_id = None
            verified.feedback = []
        elif verified.target_agent_id is None or not verified.feedback:
            return None, "승인하지 않은 Reviewer 결과에는 재실행 대상과 feedback이 필요합니다."
        if validation and not validation.get("valid"):
            first_issue = validation["issues"][0]
            if verified.approved or verified.target_agent_id != first_issue["target_agent_id"]:
                return None, "Reviewer 결과가 검증 Tool의 첫 번째 문제와 일치하지 않습니다."
    return verified, None


def invalidate_downstream(state: dict[str, object], agent_id: str) -> None:
    stage_ids = [item[0] for item in STAGES]
    start = stage_ids.index(agent_id)
    for _, field in STAGES[start + 1:]:
        state[field] = None


async def meeting_analysis_flow(request: MeetingWorkflowRequest, tracker=None) -> dict[str, object]:
    state: dict[str, object] = {
        "audio_id": request.audio_id,
        "audio_processing": None,
        "analysis": None,
        "action_items": None,
        "validation": None,
        "reviews": [],
        "retry_counts": {agent_id: 0 for agent_id, _ in STAGES},
        "pending_retry": None,
        "review_required": False,
    }
    trace: list[dict[str, object]] = []

    while len(trace) < MAX_LLM_CALLS:
        expected = expected_next(state)
        if expected == "needs_attention":
            return {"status": "needs_attention", "reason": "review_not_approved_after_retry", "state": state, "trace": trace}
        supervisor_prompt = (
            "당신은 meeting_supervisor_agent입니다. Worker 업무를 하지 말고 다음 행동만 고르세요.\n"
            f"현재 상태: {json.dumps(state, ensure_ascii=False)}\n"
            f"Python이 허용한 next_agent는 {expected}입니다. 정확히 이 값을 반환하세요."
        )
        supervisor = await run_profile(
            get_agent("meeting_supervisor_agent"), supervisor_prompt,
            MeetingSupervisorDecision, tracker,
        )
        trace.append({"step": len(trace) + 1, "actor": "meeting_supervisor_agent", "action": "select", **supervisor})
        if supervisor.get("result") is None:
            return {"status": "failed", "reason": "supervisor_failed", "state": state, "trace": trace}
        selected = supervisor["result"]["next_agent"]
        if selected != expected:
            return {"status": "blocked", "reason": "invalid_transition", "expected_next": expected, "state": state, "trace": trace}
        if selected == "finish":
            return {"status": "completed", "reason": "review_approved", "state": state, "trace": trace}

        worker = await run_profile(
            get_agent(selected), worker_prompt(selected, request, state),
            WORKER_SCHEMAS[selected], tracker,
            tool_inputs=tool_inputs(selected, request, state),
        )
        if selected == "meeting_reviewer_agent":
            state["validation"] = worker.get("tool_results", {}).get("validate_mock_meeting_result")
        verified, error = verify_worker(selected, worker)
        trace.append({"step": len(trace) + 1, "actor": selected, "action": "execute", "verification_error": error, **worker})
        if verified is None:
            return {"status": "failed", "reason": "worker_failed", "state": state, "trace": trace}

        was_retry = state["pending_retry"] == selected
        if was_retry:
            invalidate_downstream(state, selected)
        field_by_agent = dict(STAGES)
        if selected in field_by_agent:
            state[field_by_agent[selected]] = verified.model_dump()
            if was_retry:
                state["pending_retry"] = None
                state["review_required"] = True
        else:
            review = verified.model_dump()
            state["reviews"].append(review)
            state["review_required"] = False
            if not verified.approved:
                target = verified.target_agent_id
                if state["retry_counts"][target] < MAX_RETRIES_PER_WORKER:
                    state["retry_counts"][target] += 1
                    state["pending_retry"] = target

    return {"status": "failed", "reason": "max_llm_calls", "state": state, "trace": trace}


async def execute_meeting_tracked(run_id: str, request: MeetingWorkflowRequest) -> None:
    from app.observability.tracker import RunTracker

    tracker = RunTracker(run_id, MAX_LLM_CALLS + 1)
    tracker.update("orchestrator", "queued", "회의 음성 분석 실행이 등록되었습니다.")
    try:
        result = await meeting_analysis_flow(request, tracker)
        result["run_id"] = run_id
        if result["status"] == "completed":
            tracker.finish(result)
        else:
            tracker.fail(f"종료 이유: {result['reason']}", result)
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
