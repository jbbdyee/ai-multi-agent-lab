from app.schemas.contracts import AgentTask


ANALYZE_MEETING = AgentTask(
    task_id="analyze_meeting",
    agent_id="meeting_analyst_agent",
    required_input=["transcript"],
    expected_output=["summary", "key_points", "decisions"],
    completion_condition="요약이 비어 있지 않고 모든 논점과 결정사항에 원문 근거가 있음",
)

