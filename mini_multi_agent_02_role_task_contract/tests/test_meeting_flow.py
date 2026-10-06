import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.meeting_analysis_flow import run_meeting_analysis_flow  # noqa: E402
from app.schemas.contracts import MeetingAnalysisRequest  # noqa: E402


class MeetingFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_results_join_at_reviewer(self) -> None:
        responses = [
            {"status": "completed", "agent_id": "meeting_analyst_agent", "result": {"agent_id": "meeting_analyst_agent", "summary": "일정을 논의했다.", "key_points": [], "decisions": []}},
            {"status": "completed", "agent_id": "meeting_task_manager_agent", "result": {"agent_id": "meeting_task_manager_agent", "action_items": [{"description": "로그인 구현", "assignee": "민수", "due_date": "금요일", "evidence": "금요일까지 구현", "status": "ready", "missing_information": []}]}},
            {"status": "completed", "agent_id": "meeting_reviewer_agent", "result": {"agent_id": "meeting_reviewer_agent", "status": "PASS", "issues": []}},
        ]
        request = MeetingAnalysisRequest.model_validate({"transcript": [{"speaker": "민수", "content": "금요일까지 구현하겠습니다."}]})
        with patch("app.orchestration.meeting_analysis_flow.run_agent", new=AsyncMock(side_effect=responses)) as mocked:
            result = await run_meeting_analysis_flow(request)
        self.assertEqual(result.status, "completed")
        self.assertEqual(mocked.await_count, 3)
        self.assertEqual([event.phase for event in result.trace], ["parallel_analysis", "parallel_analysis", "review_join"])


if __name__ == "__main__":
    unittest.main()

