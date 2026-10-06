"""Task 정의를 모아 화면과 실행 경계에 같은 명세를 제공한다."""

from app.tasks.weather_task import CHECK_WEATHER
from app.tasks.place_task import FIND_PLACES
from app.tasks.lodging_task import CHOOSE_LODGING
from app.tasks.budget_task import ALLOCATE_BUDGET
from app.tasks.safety_task import CHECK_SAFETY
from app.tasks.itinerary_task import BUILD_ITINERARY
from app.tasks.meeting_analysis_task import ANALYZE_MEETING
from app.tasks.meeting_task_extraction_task import EXTRACT_MEETING_ACTION_ITEMS
from app.tasks.meeting_review_task import REVIEW_MEETING_RESULTS


TASKS = (
    CHECK_WEATHER, FIND_PLACES, CHOOSE_LODGING, ALLOCATE_BUDGET, CHECK_SAFETY, BUILD_ITINERARY,
    ANALYZE_MEETING, EXTRACT_MEETING_ACTION_ITEMS, REVIEW_MEETING_RESULTS,
)
TASK_BY_ID = {task.task_id: task for task in TASKS}

if len(TASK_BY_ID) != len(TASKS):
    raise ValueError("중복된 AgentTask ID가 있습니다.")
