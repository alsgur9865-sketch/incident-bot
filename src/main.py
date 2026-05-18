"""
main.py — FastAPI 앱 진입점

엔드포인트:
- GET  /                : 헬스체크
- GET  /cache/stats     : (Day 9) SQLite 캐시 통계
- POST /chat            : (Day 7) 단순 LLM 호출
- POST /chat/tools      : (Day 8/9) Tool Calling + 회복력 wrapper
- GET  /chaos           : (Day 10) 현재 CHAOS_MODE 상태
- POST /chaos/toggle    : (Day 10) CHAOS_MODE 런타임 토글 (대시보드 버튼용)
- GET  /stats           : (Day 10) 응답 통계 — 영상 "fallback N회, 응답 누락 0건" 컷
- POST /stats/reset     : (Day 10) 카운터 리셋 — 데모 직전 호출
- GET  /docs            : 자동 생성 Swagger UI

실행:
    uvicorn src.main:app --reload
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.llm_client import chat, chat_with_tools
from src import cache, stats


app = FastAPI(
    title="Incident Response Bot",
    description="절대 안 죽는 DevOps 어시스턴트 — TrueFoundry 회복력 4단 체인",
    version="0.4.0",
)


def _chaos_is_on() -> bool:
    return os.getenv("CHAOS_MODE", "").strip() in ("1", "true", "TRUE", "yes")


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="인시던트 상황 설명",
        examples=["최근 배포 이후 API가 5초 넘게 느려졌어요"],
    )


class ChatResponse(BaseModel):
    reply: str = Field(..., description="봇의 진단 + 다음 액션")


class ChatWithToolsResponse(ChatResponse):
    tool_calls_made: list[str] = Field(
        default_factory=list, description="호출된 GitHub 도구 목록"
    )
    rounds: int = Field(..., description="LLM 왕복 횟수")

    # Day 9 회복력 메타데이터 — 대시보드/영상 시각화용
    source: str = Field(
        "live", description="응답 출처: live | cache | graceful"
    )
    fallback_used: bool = Field(
        False, description="라이브 호출 실패해서 폴백 발동했나"
    )
    fallback_reason: Optional[str] = Field(
        None, description="폴백 사유 (디버깅용)"
    )
    cache_age_seconds: Optional[int] = Field(
        None, description="캐시 히트 시 응답 나이(초)"
    )
    cache_stale: Optional[bool] = Field(
        None, description="캐시 TTL 초과 여부 (graceful 우선순위 판단)"
    )


class ChaosToggleRequest(BaseModel):
    on: Optional[bool] = Field(
        None,
        description="명시적 켜기/끄기. 생략하면 현재 상태를 반전(토글).",
    )


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "incident-bot",
        "version": "0.4.0",
        "chaos_mode": _chaos_is_on(),
    }


@app.get("/cache/stats")
def cache_stats():
    """SQLite 캐시 통계 — 대시보드 '폴백 가능 응답 N건' 표시용"""
    return cache.stats()


@app.get("/chaos")
def chaos_status():
    """현재 CHAOS_MODE 상태 — 대시보드 토글 버튼 초기 상태용"""
    return {"chaos_mode": _chaos_is_on()}


@app.post("/chaos/toggle")
def chaos_toggle(req: ChaosToggleRequest = ChaosToggleRequest()):
    """
    CHAOS_MODE 런타임 토글. 서버 재시작 없이 LLM 호출을 강제 실패시킴.

    Body 옵션:
    - {"on": true}  → 강제 ON
    - {"on": false} → 강제 OFF
    - {} (생략)     → 현재 상태 반전 (토글)

    영상 4컷의 핵심 — 버튼 한 번에 "Groq 죽이기" 시연.
    """
    current = _chaos_is_on()
    new_state = (not current) if req.on is None else bool(req.on)

    if new_state:
        os.environ["CHAOS_MODE"] = "1"
    else:
        os.environ.pop("CHAOS_MODE", None)

    return {
        "chaos_mode": new_state,
        "previous": current,
        "changed": current != new_state,
    }


@app.get("/stats")
def stats_snapshot():
    """누적 응답 통계 — 영상 6컷 'fallback N회, 응답 누락 0건' 시각화용"""
    return stats.snapshot()


@app.post("/stats/reset")
def stats_reset():
    """카운터 리셋 — 데모 시작 직전에 호출"""
    stats.reset()
    return {"status": "reset", "snapshot": stats.snapshot()}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Day 7 단순 호출 — 도구 없이 LLM만 (회복력 wrapper 미적용)"""
    try:
        reply = chat(req.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM 호출 실패: {type(e).__name__}: {e}",
        )
    return ChatResponse(reply=reply)


@app.post("/chat/tools", response_model=ChatWithToolsResponse)
def chat_with_tools_endpoint(req: ChatRequest):
    """
    Day 8 Tool Calling + Day 9 회복력 wrapper.

    절대 500 안 던짐 — wrapper 내부에서 모든 예외 흡수.
    응답 source 필드로 어느 폴백 단계에서 응답했는지 확인 가능.
    """
    result = chat_with_tools(req.message)
    return ChatWithToolsResponse(
        reply=result["reply"],
        tool_calls_made=result.get("tool_calls_made", []),
        rounds=result.get("rounds", 0),
        source=result.get("source", "live"),
        fallback_used=result.get("fallback_used", False),
        fallback_reason=result.get("fallback_reason"),
        cache_age_seconds=result.get("cache_age_seconds"),
        cache_stale=result.get("cache_stale"),
    )
