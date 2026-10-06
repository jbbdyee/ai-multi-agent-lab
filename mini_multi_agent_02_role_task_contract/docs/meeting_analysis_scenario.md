# Multi-Agent 회의 분석 서비스 시나리오

## 목적

화자 구분이 완료된 회의 원문을 역할별 Agent가 병렬 분석하고, Reviewer가 원문과 결과를
비교해 검증하는 회의 후처리 서비스입니다.

## 입력과 출력

- 입력: 회의 제목(선택), 화자와 발언으로 구성된 회의 원문
- 출력: 요약, 핵심 논점, 결정사항, Action Item, Reviewer 검증 결과, 실행 Trace

## Agent와 Orchestration

```text
                    ┌→ Meeting Analyst ─┐
회의 원문 ──────────┤                   ├→ Reviewer
                    └→ Task Manager ────┘
                             ↓
 completed / needs_user_input / review_failed / failed
```

- Parallel Workers: Meeting Analyst와 Task Manager가 동일한 원문을 독립 분석합니다.
- Join: 두 결과가 Output Contract를 통과한 경우에만 Reviewer에게 전달합니다.
- Conditional Routing: Reviewer 결과와 누락 정보에 따라 Workflow 상태를 결정합니다.
- Minimum Context: 작업 Agent에는 원문만, Reviewer에는 원문과 검증된 결과만 전달합니다.

## 안전 경계

- 담당자나 기한을 추측하지 않습니다.
- 누락 정보가 있으면 `needs_confirmation`으로 표시합니다.
- 필수 Agent가 실패하면 Reviewer를 실행하지 않습니다.
- 다른 Agent의 결과를 Contract 검증 전에 전달하지 않습니다.

## Swagger API

- `GET /api/meeting/agents`
- `GET /api/meeting/tasks`
- `GET /api/meeting/contracts`
- `POST /api/meeting/contracts/validate`
- `POST /api/meeting/analyze`
- `POST /api/meeting/async-runs` — Background 실행 후 `run_id` 반환
- `GET /api/async-runs/{run_id}/snapshot` — Redis 진행 상태와 결과 조회

## 다음 확장 범위

- Reviewer가 지정한 Agent만 제한적으로 재실행
- Timeout, 최대 재시도, run_id 기반 Audit Trace
- 음성 업로드, STT, pyannote.audio 화자 분리
- 일정 등록이나 메시지 발송 전 사용자 승인
