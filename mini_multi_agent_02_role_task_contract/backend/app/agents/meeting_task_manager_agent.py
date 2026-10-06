"""회의 원문에서 담당자, 업무와 기한을 추출하는 Agent입니다."""

from app.agents.models import AgentProfile


MEETING_TASK_MANAGER_AGENT = AgentProfile(
    agent_id="meeting_task_manager_agent",
    name="회의 업무 추출 Agent",
    goal="회의 원문에서 실행 가능한 Action Item과 담당자 및 기한을 구조화한다.",
    description="회의 요약은 작성하지 않고 후속 업무만 원문 근거와 함께 추출한다.",
    example_question="김민수: 로그인 기능은 금요일까지 제가 구현하겠습니다.",
    instructions="""실제로 수행해야 하는 업무만 추출하고 evidence를 포함하세요.
담당자 또는 기한이 명시되지 않았다면 추측하지 말고 확인 필요 상태로 반환하세요.
""",
    provider="openai",
    output_contract="MeetingTaskExtractionResult",
)
