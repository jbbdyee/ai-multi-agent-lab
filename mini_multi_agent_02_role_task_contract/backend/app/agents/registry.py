"""개별 파일에 선언된 Agent를 등록하고 ID로 조회한다."""
from app.agents.models import AgentProfile
from app.agents.budget_agent import BUDGET_AGENT
from app.agents.itinerary_agent import ITINERARY_AGENT
from app.agents.place_agent import PLACE_AGENT
from app.agents.lodging_agent import LODGING_AGENT
from app.agents.safety_agent import SAFETY_AGENT
from app.agents.weather_agent import WEATHER_AGENT
from app.agents.support_analyst_agent import SUPPORT_ANALYST_AGENT
from app.agents.support_writer_agent import SUPPORT_WRITER_AGENT
from app.agents.meeting_analyst_agent import MEETING_ANALYST_AGENT
from app.agents.meeting_task_manager_agent import MEETING_TASK_MANAGER_AGENT
from app.agents.meeting_reviewer_agent import MEETING_REVIEWER_AGENT
from app.agents.meeting_supervisor_agent import MEETING_SUPERVISOR_AGENT

_PROFILES = (
    WEATHER_AGENT, PLACE_AGENT, LODGING_AGENT, BUDGET_AGENT, SAFETY_AGENT, ITINERARY_AGENT,
    SUPPORT_ANALYST_AGENT, SUPPORT_WRITER_AGENT,
    MEETING_ANALYST_AGENT, MEETING_TASK_MANAGER_AGENT, MEETING_REVIEWER_AGENT,
    MEETING_SUPERVISOR_AGENT,
)
AGENTS = {agent.agent_id: agent for agent in _PROFILES}


def get_agent(agent_id: str) -> AgentProfile:
    if agent_id not in AGENTS:
        raise ValueError(f"등록되지 않은 Agent입니다: {agent_id}")
    return AGENTS[agent_id]
