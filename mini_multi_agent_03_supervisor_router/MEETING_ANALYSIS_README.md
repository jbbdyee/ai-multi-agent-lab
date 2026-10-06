# 회의 음성 분석 Supervisor–Worker 서비스

회의 음성 데이터를 처리하여 화자를 구분하고, 회의 내용과 결정사항을 분석한 뒤 후속 업무(Action Item)를 추출·검토하는 멀티 에이전트 서비스입니다.

현재 버전은 `AUDIO-001`, `AUDIO-002` Mock 데이터를 사용합니다.

## 1. 주요 기능

- 음성 파일 메타데이터 확인
- 화자별 발화 구간 분리
- 타임스탬프 기반 음성 전사
- 화자 ID와 회의 참석자 연결
- 회의 요약, 핵심 논점 및 결정사항 분석
- 담당자, 기한 및 근거가 포함된 Action Item 추출
- 전체 결과 검토 및 대상 Worker 재실행
- 실시간 진행 상태와 실행 이력 조회
- Swagger 및 Streamlit 화면 제공

## 2. 실행 구조

```text
사용자 요청
   ↓
meeting_supervisor_agent
   ↓
audio_processing_agent ── Mock Tool 4개
   ↓
meeting_analyst_agent
   ↓
meeting_action_item_agent
   ↓
meeting_reviewer_agent ── 검증 Tool 1개
   ├─ approved=true  → finish
   └─ approved=false → 지목된 Worker 재실행 → 하위 단계 재실행 → 재검토
```

Supervisor는 현재 State를 확인하여 다음 Worker 또는 종료를 선택합니다. 실행 순서와 재실행은 `meeting_analysis.py`에서 관리합니다.

## 3. Agent 구성

| Agent | 구분 | 역할 | Tool |
|---|---|---|---|
| `meeting_supervisor_agent` | Supervisor | State를 보고 다음 Worker, `finish`, `needs_attention` 중 하나를 선택 | 없음 |
| `audio_processing_agent` | Worker | 음성 정보, 화자 구간, 전사, 참석자 매핑을 결합 | Mock Tool 4개 |
| `meeting_analyst_agent` | Worker | 전사 근거로 요약, 핵심 논점, 결정사항 분석 | 없음 |
| `meeting_action_item_agent` | Worker | 명시된 업무, 담당자, 기한과 근거 추출 | 없음 |
| `meeting_reviewer_agent` | Worker | 전체 결과를 검증하고 승인 또는 재실행 대상 결정 | 검증 Tool 1개 |

## 4. Output Contract

각 Agent와 API의 출력은 Pydantic 모델로 검증합니다.

| Contract | 적용 대상 | 주요 결과 |
|---|---|---|
| `MeetingSupervisorDecision` | Supervisor | 다음 Agent, `finish` 또는 `needs_attention` 선택 |
| `AudioProcessingResult` | 음성 처리 Worker | 음성 메타데이터, 화자 구간, 전사 및 참석자 정보 |
| `MeetingAnalysisResult` | 회의 분석 Worker | 회의 요약, 핵심 논점 및 결정사항 |
| `MeetingActionItemResult` | 업무 추출 Worker | 후속 업무, 담당자, 기한 및 근거 |
| `MeetingReviewResult` | Reviewer | 승인 여부, 재실행 대상 및 피드백 |
| `MeetingWorkflowRequest` | API 요청 | 음성 ID, 분석 요청 및 재실행 옵션 |

구현 파일은 `backend/app/schemas/workflow.py`입니다.

## 5. 회의 분석용 Mock Tool

| Tool | 역할 |
|---|---|
| `get_mock_audio_metadata` | 음성 형식, 길이, 샘플레이트 확인 |
| `run_mock_speaker_diarization` | 화자별 발화 시간 구간 반환 |
| `run_mock_speech_to_text` | 타임스탬프가 포함된 전사 결과 반환 |
| `lookup_mock_participants` | 화자 ID와 참석자 정보 연결 |
| `validate_mock_meeting_result` | 필수값, 화자 매핑, 분석 결과와 Action Item 검증 |

Mock 데이터는 `AUDIO-001`, `AUDIO-002` 두 가지를 제공합니다. Tool 구현은 `mcp_server/tools/support_tools.py`, MCP 등록은 `mcp_server/main.py`에서 확인할 수 있습니다.

## 6. 오케스트레이션과 재실행

오케스트레이션은 `backend/app/orchestration/meeting_analysis.py`에 있습니다.

1. Python의 `expected_next()`가 현재 State에서 허용되는 다음 단계를 계산합니다.
2. Supervisor LLM이 다음 Agent를 선택합니다.
3. Worker가 담당 작업을 실행하고 결과를 State에 저장합니다.
4. Reviewer가 승인하면 `completed`로 종료합니다.
5. Reviewer가 거절하면 `target_agent_id`로 지정된 Worker를 최대 1회 재실행합니다.
6. 상위 Worker를 재실행하면 영향을 받는 하위 결과를 다시 생성합니다.
7. 재실행 후에도 승인되지 않으면 `needs_attention`으로 종료합니다.

무한 반복을 방지하기 위해 Worker별 재실행 횟수와 전체 LLM 호출 횟수에 제한이 있습니다.

## 7. 주요 구현 파일

| 구분 | 파일 |
|---|---|
| Worker YAML | `backend/app/agents/definitions/workers.yaml` |
| Supervisor 선언 | `backend/app/agents/meeting_supervisor_agent.py` |
| Agent 로딩·등록 | `backend/app/agents/loader.py`, `backend/app/agents/registry.py` |
| Output Contract | `backend/app/schemas/workflow.py` |
| Mock Tool | `mcp_server/tools/support_tools.py` |
| MCP Tool 등록 | `mcp_server/main.py` |
| Orchestration | `backend/app/orchestration/meeting_analysis.py` |
| Engine 연결 | `backend/app/orchestration/engine.py` |
| API Router | `backend/app/routers/workflow.py` |
| 프론트엔드 | `frontend/app.py`의 `10 · 회의 음성 분석 서비스` |
| 테스트 | `tests/test_meeting_analysis.py` |

## 8. 실행 준비

프로젝트 폴더에서 가상환경을 활성화하고 의존성을 설치합니다. 이미 설치했다면 설치 명령은 생략할 수 있습니다.

```powershell
cd C:\mini_multi_agent\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`.env`에 사용할 LLM Provider의 API Key를 설정합니다. 현재 회의 분석 Agent의 기본 Provider는 OpenAI입니다.

```env
OPENAI_API_KEY=발급받은_API_KEY
OPENAI_MODEL=gpt-4.1-mini
```

## 9. 서버 실행

각 서버는 별도의 터미널에서 실행합니다.

### MCP 서버

```powershell
cd C:\mini_multi_agent\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
python .\mcp_server\main.py
```

### FastAPI 백엔드

```powershell
cd C:\mini_multi_agent\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000 --app-dir backend
```

### Streamlit 프론트엔드

```powershell
cd C:\mini_multi_agent\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port 8530
```

- Swagger: <http://127.0.0.1:8000/docs>
- 프론트엔드: <http://localhost:8530>

같은 네트워크의 다른 PC에서 접속할 수 있도록 실행하려면 다음 명령을 사용합니다.

```powershell
streamlit run .\frontend\app.py --server.address 0.0.0.0 --server.port 8530
```

접속 주소는 `http://현재_PC의_IP:8530`입니다.

## 10. Swagger 테스트

### 동기 실행

Swagger에서 `Meeting Analysis` → `POST /api/runs/meeting-analysis` → **Try it out**을 선택하고 다음 JSON을 실행합니다.

```json
{
  "audio_id": "AUDIO-001",
  "request": "회의 음성을 처리하고 Action Item을 추출한 뒤 결과를 검토해 주세요.",
  "demonstrate_revision": false
}
```

정상 결과에서는 다음 항목을 확인합니다.

- `status`: `completed`
- `reason`: `review_approved`
- `state.audio_processing`: 화자 구간, 전사, 참석자 정보
- `state.analysis`: 회의 요약과 결정사항
- `state.action_items`: 후속 업무
- `state.reviews`: Reviewer의 승인 결과
- `trace`: Supervisor 선택과 Worker 실행 기록

### 재실행 흐름 확인

`demonstrate_revision`을 `true`로 보내면 첫 검토 거절과 Worker 재실행 흐름을 확인할 수 있습니다.

```json
{
  "audio_id": "AUDIO-001",
  "request": "회의 음성을 처리하고 Action Item을 추출한 뒤 결과를 검토해 주세요.",
  "demonstrate_revision": true
}
```

Trace에서 Reviewer 거절 → 대상 Worker 재실행 → 필요한 하위 단계 재실행 → Reviewer 재검토 흐름을 확인할 수 있습니다.

### 비동기 실행과 진행 상태 확인

1. `POST /api/async-runs/meeting-analysis`를 같은 요청 본문으로 실행합니다.
2. 응답의 `run_id`를 복사합니다.
3. `GET /api/async-runs/{run_id}/snapshot`에 붙여 넣어 실행합니다.
4. `status`, `progress_percent`, `current_agent`, `result`, 실행 이력을 확인합니다.

### Tool 등록 확인

`GET /api/mcp-status`를 실행하여 회의 분석용 Tool 5개가 등록됐는지 확인합니다.

## 11. 프론트엔드 테스트

1. <http://localhost:8530>에 접속합니다.
2. 왼쪽 메뉴에서 `10 · 회의 음성 분석 서비스`를 선택합니다.
3. `AUDIO-001` 또는 `AUDIO-002`를 선택합니다.
4. 필요하면 `첫 검토 실패 후 Worker 재실행 흐름 보기`를 체크합니다.
5. `회의 분석 실행`을 누릅니다.
6. 실행 중 표시되는 진행률, 현재 Agent와 `실시간 실행 이력`을 확인합니다.
7. 완료 후 결과 State와 `실행 Trace`를 확인합니다.

프론트엔드는 `POST /api/async-runs/meeting-analysis`로 실행을 등록한 뒤,
`GET /api/async-runs/{run_id}/snapshot`을 1초마다 호출합니다. 따라서 실행이 끝난 뒤에만
결과를 보여주는 것이 아니라 Supervisor의 선택과 각 Worker의 시작·완료 상태가 실행 이력에
순서대로 나타납니다. 이력은 Redis Stream에, 현재 진행 상태는 Redis Hash에 저장됩니다.

```text
실행 ID
진행률
현재 Agent · 현재 단계 · 상태 메시지
실시간 실행 이력 표
완료 후 실행 Trace와 최종 State
```

`worker_failed`가 표시되면 Trace의 마지막 Worker 항목을 열어 `error`, `verification_error`, `tool_results`를 먼저 확인합니다. 터미널의 FastAPI 로그에서도 Provider 오류나 API Key 문제를 확인할 수 있습니다.

## 12. 테스트 코드 실행

```powershell
cd C:\mini_multi_agent\mini_multi_agent_03_supervisor_router
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

회의 분석 기능만 테스트하려면 다음 명령을 사용합니다.

```powershell
python -m unittest tests.test_meeting_analysis -v
```
