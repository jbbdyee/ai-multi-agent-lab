import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestration.meeting_analysis_flow import execute_meeting_tracked  # noqa: E402
from app.schemas.contracts import MeetingAnalysisRequest, MeetingWorkflowResult  # noqa: E402


class MeetingAsyncFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_tracked_execution_finishes_snapshot_for_business_result(self) -> None:
        request = MeetingAnalysisRequest.model_validate({
            "transcript": [{"speaker": "민수", "content": "담당자는 나중에 정하겠습니다."}]
        })
        result = MeetingWorkflowResult(status="needs_user_input")
        tracker = MagicMock()

        with patch(
            "app.orchestration.meeting_analysis_flow.RunTracker",
            return_value=tracker,
        ), patch(
            "app.orchestration.meeting_analysis_flow.run_meeting_analysis_flow",
            new=AsyncMock(return_value=result),
        ):
            await execute_meeting_tracked("run-test", request)

        tracker.start.assert_called_once()
        tracker.finish.assert_called_once()
        tracker.fail.assert_not_called()
        self.assertEqual(tracker.finish.call_args.args[0]["run_id"], "run-test")


if __name__ == "__main__":
    unittest.main()

