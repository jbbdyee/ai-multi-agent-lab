import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.contracts import MeetingActionItem, MeetingReviewResult  # noqa: E402


class MeetingContractTests(unittest.TestCase):
    def test_missing_assignee_requires_confirmation(self) -> None:
        item = MeetingActionItem.model_validate({
            "description": "배포 준비",
            "assignee": None,
            "due_date": "금요일",
            "evidence": "금요일까지 배포를 준비해야 합니다.",
            "status": "needs_confirmation",
            "missing_information": ["assignee"],
        })
        self.assertEqual(item.status, "needs_confirmation")

    def test_fail_review_requires_issue(self) -> None:
        with self.assertRaises(ValidationError):
            MeetingReviewResult.model_validate({"status": "FAIL", "issues": []})


if __name__ == "__main__":
    unittest.main()

