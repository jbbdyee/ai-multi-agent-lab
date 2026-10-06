"""회의 원문에서 요약, 핵심 논점과 결정사항을 추출하는 Agent입니다."""

from app.agents.models import AgentProfile


MEETING_ANALYST_AGENT = AgentProfile(
    agent_id="meeting_analyst_agent",
    name="회의 분석 Agent",
    goal="회의 원문에서 핵심 내용, 주요 논점과 결정사항을 구조화한다.",
    description="Action Item은 담당하지 않고 회의 내용과 명시적인 합의만 분석한다.",
    example_question="김민수: 로그인 기능은 금요일까지 구현하겠습니다.",
    instructions="""회의 원문만 사용해 요약, 주요 논점과 명시적인 결정사항을 정리하세요.
각 결과에는 원문에서 확인할 수 있는 evidence를 포함하세요.
불명확한 발언을 결정사항으로 확정하지 마세요.
""",
    provider="openai",
    output_contract="MeetingAnalysisResult",
)
