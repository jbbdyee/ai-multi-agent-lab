import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.supervisor_meeting_flow import run_supervisor_meeting_flow  # noqa: E402
from app.schemas.contracts import MeetingAnalysisRequest  # noqa: E402
from app.services.worker_definition_service import load_worker_definitions  # noqa: E402


class SupervisorMeetingFlowTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        load_worker_definitions.cache_clear()

    async def test_yaml_workers_are_tool_free(self) -> None:
        workers = load_worker_definitions()
        self.assertEqual(
            set(workers),
            {"meeting_analyst_agent", "meeting_task_manager_agent", "meeting_reviewer_agent"},
        )
        self.assertTrue(all(not worker.allowed_tools for worker in workers.values()))
        self.assertTrue(all(worker.goal for worker in workers.values()))
        self.assertTrue(all(worker.instructions for worker in workers.values()))
        self.assertTrue(all(worker.provider == "openai" for worker in workers.values()))

    async def test_llm_supervisor_routes_workers_until_finish(self) -> None:
        responses = [
            {"result": {"agent_id": "meeting_supervisor_agent", "next_worker": "meeting_analyst_agent", "reason": "분석 필요"}},
            {"result": {"agent_id": "meeting_analyst_agent", "summary": "일정 논의", "key_points": [], "decisions": []}},
            {"result": {"agent_id": "meeting_supervisor_agent", "next_worker": "meeting_task_manager_agent", "reason": "업무 추출 필요"}},
            {"result": {"agent_id": "meeting_task_manager_agent", "action_items": [{"description": "로그인 구현", "assignee": "김민수", "due_date": "금요일", "evidence": "금요일까지 구현", "status": "ready", "missing_information": []}]}},
            {"result": {"agent_id": "meeting_supervisor_agent", "next_worker": "meeting_reviewer_agent", "reason": "검증 필요"}},
            {"result": {"agent_id": "meeting_reviewer_agent", "status": "PASS", "issues": []}},
            {"result": {"agent_id": "meeting_supervisor_agent", "next_worker": "finish", "reason": "검증 완료"}},
        ]
        for response in responses:
            response.update({"status": "completed", "error": None})
        request = MeetingAnalysisRequest.model_validate({
            "transcript": [{"speaker": "김민수", "content": "금요일까지 구현하겠습니다."}]
        })

        with patch(
            "app.orchestration.supervisor_meeting_flow.run_agent",
            new=AsyncMock(side_effect=responses),
        ) as mocked:
            result = await run_supervisor_meeting_flow(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(mocked.await_count, 7)
        self.assertEqual(
            result.completed_workers,
            ["meeting_analyst_agent", "meeting_task_manager_agent", "meeting_reviewer_agent"],
        )


if __name__ == "__main__":
    unittest.main()
