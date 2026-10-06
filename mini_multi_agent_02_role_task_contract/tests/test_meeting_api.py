import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402


class MeetingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_openapi_contains_meeting_routes(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/meeting/agents", paths)
        self.assertIn("/api/meeting/tasks", paths)
        self.assertIn("/api/meeting/contracts", paths)
        self.assertIn("/api/meeting/contracts/validate", paths)
        self.assertIn("/api/meeting/analyze", paths)
        self.assertIn("/api/meeting/async-runs", paths)
        self.assertIn("/api/async-runs/{run_id}/snapshot", paths)

    def test_meeting_contract_validation_route(self) -> None:
        response = self.client.post(
            "/api/meeting/contracts/validate",
            json={
                "contract_name": "MeetingReviewResult",
                "payload": {
                    "agent_id": "meeting_reviewer_agent",
                    "status": "FAIL",
                    "issues": [],
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])


if __name__ == "__main__":
    unittest.main()
