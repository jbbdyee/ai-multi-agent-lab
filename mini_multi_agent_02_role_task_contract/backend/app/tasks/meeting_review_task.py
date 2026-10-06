from app.schemas.contracts import AgentTask


REVIEW_MEETING_RESULTS = AgentTask(
    task_id="review_meeting_results",
    agent_id="meeting_reviewer_agent",
    required_input=["transcript", "meeting_analysis", "task_extraction"],
    expected_output=["status", "issues"],
    completion_condition="PASS에는 이슈가 없고 FAIL에는 대상 Agent가 명시된 이슈가 하나 이상 있음",
)

