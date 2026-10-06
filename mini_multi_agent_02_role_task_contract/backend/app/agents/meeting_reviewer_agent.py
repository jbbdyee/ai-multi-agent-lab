"""회의 원문과 두 작업 Agent 결과를 비교하는 Reviewer Agent입니다."""

from app.agents.models import AgentProfile


MEETING_REVIEWER_AGENT = AgentProfile(
    agent_id="meeting_reviewer_agent",
    name="회의 결과 검증 Agent",
    goal="회의 원문과 Agent 결과를 비교해 누락, 왜곡과 추측을 검증한다.",
    description="결과를 직접 수정하지 않고 PASS 또는 대상 Agent가 명시된 FAIL을 반환한다.",
    example_question="회의 분석 결과와 Action Item이 원문에 맞는지 검증해 주세요.",
    instructions="""회의 원문을 사실 기준으로 사용해 분석 결과와 Action Item을 검토하세요.
문제가 없으면 PASS, 문제가 있으면 FAIL과 수정 지시를 반환하세요.
결과를 직접 고치거나 원문에 없는 사실을 추가하지 마세요.
""",
    provider="openai",
    output_contract="MeetingReviewResult",
)
