"""현재 State를 보고 다음 회의 Worker를 선택하는 LLM Supervisor입니다."""

from app.agents.models import AgentProfile


MEETING_SUPERVISOR_AGENT = AgentProfile(
    agent_id="meeting_supervisor_agent",
    name="회의 분석 Supervisor Agent",
    goal="현재 회의 분석 State를 확인하고 다음 Worker 또는 종료 상태를 선택한다.",
    description="회의 내용을 직접 분석하지 않고 등록된 Worker 사이의 Routing만 결정한다.",
    example_question="현재 State에서 다음에 실행할 회의 Worker를 선택해 주세요.",
    instructions="""당신은 회의 분석 Workflow의 Supervisor AI Agent입니다.
직접 회의를 요약하거나 Action Item을 작성하지 말고 다음 Worker만 선택하세요.
meeting_analysis가 없으면 meeting_analyst_agent를 선택하세요.
task_extraction이 없으면 meeting_task_manager_agent를 선택하세요.
두 결과가 있고 review가 없으면 meeting_reviewer_agent를 선택하세요.
review가 PASS이고 확인할 누락 정보가 없으면 finish를 선택하세요.
담당자 또는 기한 확인이 필요하면 needs_user_input을 선택하세요.
review가 FAIL이면 issues의 target_agent_id에 대응하는 Worker를 선택하세요.
제공된 Worker 목록에 없는 이름을 만들지 마세요.
""",
    provider="openai",
    output_contract="SupervisorDecision",
)
