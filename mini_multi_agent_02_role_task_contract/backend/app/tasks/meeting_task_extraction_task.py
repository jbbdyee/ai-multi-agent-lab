from app.schemas.contracts import AgentTask


EXTRACT_MEETING_ACTION_ITEMS = AgentTask(
    task_id="extract_meeting_action_items",
    agent_id="meeting_task_manager_agent",
    required_input=["transcript"],
    expected_output=["action_items"],
    completion_condition="모든 업무에 원문 근거가 있고 누락된 담당자와 기한을 추측하지 않음",
)

