from mcp_server.database import support_queries as db

def get_order_status(order_id: str) -> dict:
    """PostgreSQL에서 주문 배송 상태를 조회합니다."""
    row = db.order(order_id.upper())
    return {"success": row is not None, "order": row, "source": "postgresql"}
def get_refund_policy() -> dict:
    """PostgreSQL에서 현재 환불 정책을 조회합니다."""
    row = db.refund_policy()
    return {"success": row is not None, "policy": row, "source": "postgresql"}
def search_help_article(topic: str) -> dict:
    """PostgreSQL에서 기술지원 문서를 조회합니다."""
    row = db.help_article(topic)
    return {"success": row is not None, "article": row, "source": "postgresql"}


MOCK_AUDIO = {
    "AUDIO-001": {
        "metadata": {"format": "wav", "duration_seconds": 18.0, "sample_rate": 16000, "channels": 1, "valid": True},
        "diarization": [
            {"speaker_id": "SPEAKER_00", "start": 0.0, "end": 5.0},
            {"speaker_id": "SPEAKER_01", "start": 5.0, "end": 10.0},
            {"speaker_id": "SPEAKER_02", "start": 10.0, "end": 14.0},
            {"speaker_id": "SPEAKER_00", "start": 14.0, "end": 18.0},
        ],
        "transcript": [
            {"start": 0.0, "end": 5.0, "text": "로그인 API는 제가 금요일까지 구현하겠습니다."},
            {"start": 5.0, "end": 10.0, "text": "화면 디자인은 수요일까지 완료하겠습니다."},
            {"start": 10.0, "end": 14.0, "text": "다음 주 월요일에 통합 테스트를 진행하겠습니다."},
            {"start": 14.0, "end": 18.0, "text": "그 일정으로 진행하겠습니다."},
        ],
        "participants": [
            {"speaker_id": "SPEAKER_00", "name": "김민수", "department": "백엔드팀"},
            {"speaker_id": "SPEAKER_01", "name": "이지은", "department": "디자인팀"},
            {"speaker_id": "SPEAKER_02", "name": "박준호", "department": "QA팀"},
        ],
    },
    "AUDIO-002": {
        "metadata": {"format": "mp3", "duration_seconds": 9.0, "sample_rate": 44100, "channels": 1, "valid": True},
        "diarization": [
            {"speaker_id": "SPEAKER_00", "start": 0.0, "end": 5.0},
            {"speaker_id": "SPEAKER_01", "start": 5.0, "end": 9.0},
        ],
        "transcript": [
            {"start": 0.0, "end": 5.0, "text": "배포 체크리스트를 목요일까지 정리하겠습니다."},
            {"start": 5.0, "end": 9.0, "text": "장애 대응 연락망은 제가 갱신하겠습니다."},
        ],
        "participants": [
            {"speaker_id": "SPEAKER_00", "name": "이지은", "department": "디자인팀"},
            {"speaker_id": "SPEAKER_01", "name": "박준호", "department": "QA팀"},
        ],
    },
}


def _mock_audio(audio_id: str) -> tuple[str, dict | None]:
    normalized = audio_id.upper()
    return normalized, MOCK_AUDIO.get(normalized)


def get_mock_audio_metadata(audio_id: str) -> dict:
    """실습용 음성 파일 메타데이터를 반환합니다."""
    normalized, audio = _mock_audio(audio_id)
    return {"success": audio is not None, "audio_id": normalized, "metadata": audio["metadata"] if audio else None, "source": "mock"}


def run_mock_speaker_diarization(audio_id: str) -> dict:
    """pyannote.audio 대신 화자별 시간 구간을 반환합니다."""
    normalized, audio = _mock_audio(audio_id)
    return {"success": audio is not None, "audio_id": normalized, "segments": audio["diarization"] if audio else [], "source": "mock"}


def run_mock_speech_to_text(audio_id: str) -> dict:
    """Whisper 대신 타임스탬프가 포함된 전사 결과를 반환합니다."""
    normalized, audio = _mock_audio(audio_id)
    return {"success": audio is not None, "audio_id": normalized, "language": "ko", "segments": audio["transcript"] if audio else [], "source": "mock"}


def lookup_mock_participants(audio_id: str) -> dict:
    """회의 초대 목록 대신 화자 ID와 참석자 정보를 반환합니다."""
    normalized, audio = _mock_audio(audio_id)
    return {"success": audio is not None, "audio_id": normalized, "participants": audio["participants"] if audio else [], "source": "mock"}


def validate_mock_meeting_result(
    audio_id: str,
    audio_metadata: dict,
    speaker_segments: list[dict],
    transcript: list[dict],
    participants: list[dict],
    analysis: dict,
    action_items: dict,
) -> dict:
    """전체 회의 처리 결과의 필수값과 화자 매핑을 Mock 규칙으로 검사합니다."""
    issues = []
    if not audio_metadata or not audio_metadata.get("valid"):
        issues.append({"target_agent_id": "audio_processing_agent", "message": "유효한 음성 메타데이터가 없습니다."})
    if not speaker_segments:
        issues.append({"target_agent_id": "audio_processing_agent", "message": "화자 구간이 없습니다."})
    if not transcript:
        issues.append({"target_agent_id": "audio_processing_agent", "message": "전사 구간이 없습니다."})
    speaker_ids = {item.get("speaker_id") for item in speaker_segments}
    participant_ids = {item.get("speaker_id") for item in participants}
    if speaker_ids - participant_ids:
        issues.append({"target_agent_id": "audio_processing_agent", "message": "참석자와 연결되지 않은 화자가 있습니다."})
    if not analysis or not analysis.get("summary"):
        issues.append({"target_agent_id": "meeting_analyst_agent", "message": "회의 요약이 없습니다."})
    items = action_items.get("action_items", []) if action_items else []
    if not items or any(not item.get("evidence") for item in items):
        issues.append({"target_agent_id": "meeting_action_item_agent", "message": "근거가 있는 Action Item이 필요합니다."})
    return {"success": True, "audio_id": audio_id.upper(), "valid": not issues, "issues": issues, "source": "mock"}
