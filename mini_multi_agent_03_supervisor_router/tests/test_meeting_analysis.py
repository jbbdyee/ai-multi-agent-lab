import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.registry import AGENTS  # noqa: E402
from app.main import app  # noqa: E402
from app.orchestration.meeting_analysis import meeting_analysis_flow  # noqa: E402
from app.schemas.workflow import MeetingWorkflowRequest  # noqa: E402
from app.services.catalog import LABS  # noqa: E402
from mcp_server.main import mcp  # noqa: E402
from mcp_server.tools.support_tools import (  # noqa: E402
    get_mock_audio_metadata, lookup_mock_participants,
    run_mock_speaker_diarization, run_mock_speech_to_text,
    validate_mock_meeting_result,
)


REQUEST = MeetingWorkflowRequest(audio_id="AUDIO-001")


def completed(result: dict, tool_results: dict | None = None) -> dict:
    return {"status": "completed", "result": result, "tool_results": tool_results or {}}


def supervisor(next_agent: str) -> dict:
    return completed({"agent_id": "meeting_supervisor_agent", "next_agent": next_agent, "reason": "현재 상태"})


AUDIO_PROCESSING = completed({
    "agent_id": "audio_processing_agent", "audio_id": "AUDIO-001",
    "audio_metadata": {"format": "wav", "duration_seconds": 18.0, "sample_rate": 16000, "channels": 1, "valid": True},
    "speaker_segments": [{"speaker_id": "SPEAKER_00", "start": 0.0, "end": 5.0}],
    "language": "ko",
    "transcript": [{"start": 0.0, "end": 5.0, "text": "로그인 API는 금요일까지 구현하겠습니다."}],
    "participants": [{"speaker_id": "SPEAKER_00", "name": "김민수", "department": "백엔드팀"}],
})
ANALYSIS = completed({
    "agent_id": "meeting_analyst_agent", "summary": "로그인 API 일정을 논의했다.",
    "key_points": [{"content": "로그인 API 구현", "evidence": "금요일까지 구현"}], "decisions": [],
})
ACTION_ITEMS = completed({
    "agent_id": "meeting_action_item_agent",
    "action_items": [{"description": "로그인 API 구현", "assignee": "김민수", "due_date": "금요일", "evidence": "금요일까지 구현"}],
})


def reviewer(approved: bool) -> dict:
    return completed(
        {
            "agent_id": "meeting_reviewer_agent", "approved": approved,
            "target_agent_id": None if approved else "audio_processing_agent",
            # 실제 LLM이 승인 응답에도 설명성 feedback을 넣을 수 있어 Orchestrator가 정규화합니다.
            "feedback": ["검증 완료"] if approved else ["음성 처리 결과를 다시 확인하세요."],
            "reason": "Mock 검증 결과",
        },
        {"validate_mock_meeting_result": {"success": True, "valid": True, "issues": [], "source": "mock"}},
    )


def initial_sequence(review_approved: bool) -> list[dict]:
    return [
        supervisor("audio_processing_agent"), AUDIO_PROCESSING,
        supervisor("meeting_analyst_agent"), ANALYSIS,
        supervisor("meeting_action_item_agent"), ACTION_ITEMS,
        supervisor("meeting_reviewer_agent"), reviewer(review_approved),
    ]


class MeetingAnalysisTests(unittest.IsolatedAsyncioTestCase):
    def test_four_workers_and_five_mock_tools_are_registered(self) -> None:
        worker_ids = {
            "audio_processing_agent", "meeting_analyst_agent",
            "meeting_action_item_agent", "meeting_reviewer_agent",
        }
        self.assertTrue(worker_ids <= set(AGENTS))
        removed_ids = {
            "audio_inspector_agent", "speaker_diarization_agent",
            "speech_to_text_agent", "participant_mapper_agent",
        }
        self.assertFalse(removed_ids & set(AGENTS))
        meeting_tools = {
            "get_mock_audio_metadata", "run_mock_speaker_diarization",
            "run_mock_speech_to_text", "lookup_mock_participants",
            "validate_mock_meeting_result",
        }
        self.assertTrue(meeting_tools <= set(mcp._tool_manager._tools))
        self.assertEqual(AGENTS["audio_processing_agent"].allowed_tools, frozenset(meeting_tools - {"validate_mock_meeting_result"}))

    def test_mock_tools_return_connected_audio_pipeline_data(self) -> None:
        metadata = get_mock_audio_metadata("AUDIO-001")
        diarization = run_mock_speaker_diarization("AUDIO-001")
        transcript = run_mock_speech_to_text("AUDIO-001")
        participants = lookup_mock_participants("AUDIO-001")
        self.assertEqual(
            {item["speaker_id"] for item in diarization["segments"]},
            {item["speaker_id"] for item in participants["participants"]},
        )
        validation = validate_mock_meeting_result(
            "AUDIO-001", metadata["metadata"], diarization["segments"], transcript["segments"],
            participants["participants"], {"summary": "요약"}, {"action_items": [{"evidence": "근거"}]},
        )
        self.assertTrue(validation["valid"])

    def test_swagger_contains_meeting_routes(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/api/runs/meeting-analysis", paths)
        self.assertIn("/api/async-runs/meeting-analysis", paths)

    def test_lab_10_frontend_is_registered(self) -> None:
        self.assertIn("10", LABS)
        frontend = (ROOT / "frontend" / "app.py").read_text(encoding="utf-8")
        self.assertIn('"10 · 회의 음성 분석 서비스"', frontend)
        self.assertIn('elif lab_id == "10":', frontend)

    async def test_simplified_pipeline_finishes_after_review(self) -> None:
        responses = [*initial_sequence(True), supervisor("finish")]
        with patch("app.orchestration.meeting_analysis.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            result = await meeting_analysis_flow(REQUEST)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.await_count, 9)
        self.assertEqual(result["state"]["reviews"][0]["feedback"], [])

    async def test_audio_retry_invalidates_and_rebuilds_downstream(self) -> None:
        responses = [
            *initial_sequence(False),
            supervisor("audio_processing_agent"), AUDIO_PROCESSING,
            supervisor("meeting_analyst_agent"), ANALYSIS,
            supervisor("meeting_action_item_agent"), ACTION_ITEMS,
            supervisor("meeting_reviewer_agent"), reviewer(True),
            supervisor("finish"),
        ]
        with patch("app.orchestration.meeting_analysis.run_profile", new_callable=AsyncMock, side_effect=responses) as run:
            result = await meeting_analysis_flow(REQUEST)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["state"]["retry_counts"]["audio_processing_agent"], 1)
        self.assertEqual(len(result["state"]["reviews"]), 2)
        self.assertEqual(run.await_count, 17)

    async def test_second_rejection_stops_for_human_attention(self) -> None:
        responses = [
            *initial_sequence(False),
            supervisor("audio_processing_agent"), AUDIO_PROCESSING,
            supervisor("meeting_analyst_agent"), ANALYSIS,
            supervisor("meeting_action_item_agent"), ACTION_ITEMS,
            supervisor("meeting_reviewer_agent"), reviewer(False),
        ]
        with patch("app.orchestration.meeting_analysis.run_profile", new_callable=AsyncMock, side_effect=responses):
            result = await meeting_analysis_flow(REQUEST)
        self.assertEqual(result["status"], "needs_attention")

    async def test_wrong_supervisor_transition_is_blocked(self) -> None:
        with patch(
            "app.orchestration.meeting_analysis.run_profile", new_callable=AsyncMock,
            return_value=supervisor("meeting_reviewer_agent"),
        ):
            result = await meeting_analysis_flow(REQUEST)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["expected_next"], "audio_processing_agent")


if __name__ == "__main__":
    unittest.main()
