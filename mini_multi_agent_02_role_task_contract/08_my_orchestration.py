"""오늘의 실습: Tool 없이 LLM Supervisor가 회의 Worker를 Routing합니다."""

import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.orchestration.supervisor_meeting_flow import run_supervisor_meeting_flow  # noqa: E402
from app.schemas.contracts import MeetingAnalysisRequest  # noqa: E402


SAMPLE_REQUEST = MeetingAnalysisRequest.model_validate({
    "title": "개발 일정 회의",
    "transcript": [
        {"speaker": "김민수", "content": "로그인 API는 제가 금요일까지 구현하겠습니다."},
        {"speaker": "이지은", "content": "화면 디자인은 수요일까지 완료하겠습니다."},
        {"speaker": "김민수", "content": "그 일정으로 진행하겠습니다."},
    ],
})


async def main() -> None:
    result = await run_supervisor_meeting_flow(SAMPLE_REQUEST)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

