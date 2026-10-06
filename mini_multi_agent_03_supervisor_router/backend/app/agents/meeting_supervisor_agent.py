"""회의 분석 State를 보고 다음 Worker를 선택하는 Supervisor."""

from app.agents.models import AgentProfile


MEETING_SUPERVISOR_AGENT = AgentProfile(
    agent_id="meeting_supervisor_agent",
    name="회의 분석 Supervisor Agent",
    goal="회의 음성 처리 상태와 검토 결과를 보고 다음 Worker 또는 종료를 선택한다.",
    description="음성 처리·회의 분석·업무 추출·검토 Worker와 재실행을 조정합니다.",
    example_question="AUDIO-001 회의 음성을 분석하고 후속 업무를 검토해 줘.",
    instructions="""Worker 업무를 대신 수행하지 마세요.
현재 State와 허용된 다음 행동을 보고 Agent 하나, finish 또는 needs_attention만 선택하세요.
Reviewer가 승인을 거절하면 지목된 Worker를 다시 선택하세요.
상위 단계가 재실행되면 무효화된 하위 단계도 순서대로 다시 실행하세요.
승인되지 않은 결과를 완료했다고 선언하지 마세요.
""",
    provider="openai",
    output_contract="MeetingSupervisorDecision",
)
