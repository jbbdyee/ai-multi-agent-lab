from functools import lru_cache
from pathlib import Path

import yaml

from app.agents.registry import AGENTS
from app.schemas.contracts import CONTRACTS
from app.schemas.supervisor_contracts import WorkerDefinition, WorkerDefinitions


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKER_DEFINITIONS_PATH = PROJECT_ROOT / "worker_definitions.yaml"


@lru_cache
def load_worker_definitions(
    path: Path = WORKER_DEFINITIONS_PATH,
) -> dict[str, WorkerDefinition]:
    """YAML Worker 선언을 검증하고 Agent ID 기준 Registry로 반환합니다."""

    if not path.is_file():
        raise FileNotFoundError(f"Worker 정의 파일을 찾을 수 없습니다: {path}")
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    definitions = WorkerDefinitions.model_validate(raw)

    registry: dict[str, WorkerDefinition] = {}
    for agent_id, worker in definitions.workers.items():
        if agent_id not in AGENTS:
            raise ValueError(
                f"등록되지 않은 Agent입니다: {agent_id}"
            )
        if worker.output_contract not in CONTRACTS:
            raise ValueError(
                f"{agent_id}가 등록되지 않은 Contract를 참조합니다: {worker.output_contract}"
            )
        agent = AGENTS[agent_id]
        if worker.goal.strip() != agent.goal.strip():
            raise ValueError(
                f"{agent_id}의 Agent와 YAML goal이 일치하지 않습니다."
            )
        if worker.instructions.strip() != agent.instructions.strip():
            raise ValueError(
                f"{agent_id}의 Agent와 YAML instructions가 일치하지 않습니다."
            )
        if worker.provider != agent.provider:
            raise ValueError(
                f"{agent_id}의 Agent와 YAML provider가 일치하지 않습니다."
            )
        if agent.output_contract != worker.output_contract:
            raise ValueError(
                f"{agent_id}의 Agent와 YAML Output Contract가 일치하지 않습니다."
            )
        if worker.allowed_tools or agent.allowed_tools:
            raise ValueError(
                f"오늘 실습 Worker는 Tool을 사용할 수 없습니다: {agent_id}"
            )
        registry[agent_id] = worker
    return registry
