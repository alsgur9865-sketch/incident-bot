"""
llm_client.py — TrueFoundry Gateway 호출 + Tool Calling + 회복력 wrapper

Day 7 (A안): chat() — 단순 호출
Day 8 (C안): _chat_with_tools_live() — LLM이 GitHub 도구 자율 호출
Day 9: chat_with_tools() — 회복력 wrapper (캐시 + graceful)

회복력 4단 체인:
    1. Groq llama-3.3-70b   ─┐
    2. Gemini 2.5 flash-lite  ├─ 게이트웨이가 자동 fallback (TrueFoundry)
    3. SQLite 캐시 (stale OK)─┐
    4. Graceful 정적 메시지   ├─ 어플리케이션 레이어 (이 파일)
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

from src.tools import TOOL_SCHEMAS, execute_tool
from src import cache, stats

load_dotenv()

_API_KEY = os.getenv("TFY_API_KEY")
_BASE_URL = os.getenv("TFY_BASE_URL")
_MODEL = os.getenv("TFY_MODEL")

_client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)

SYSTEM_PROMPT = (
    "You are a senior DevOps assistant helping with IT incident response. "
    "When the user describes an incident, respond in this exact order: "
    "(1) one-line diagnosis, (2) one or two things to check first, (3) one immediate mitigation action. "
    "Available tools: "
    "GitHub (get_recent_commits, get_recent_pulls) — recent code changes; "
    "Sentry (sentry_get_recent_errors) — surging errors; "
    "Logs (logs_tail) — per-service log lines. "
    "If you cannot tell whether the incident is code/error/log related, combine two or three tools before giving a synthesized diagnosis. "
    "Always respond in English. Be concise and friendly."
)

EXTRA_HEADERS = {
    "X-TFY-METADATA": "{}",
    "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
}


# ─────────────────────────────────────────────────────────
# Chaos toggle — 데모용 강제 실패 (Day 10에서 본격 사용)
# `os.environ["CHAOS_MODE"] = "1"` 켜면 모든 LLM 호출이 실패
# ─────────────────────────────────────────────────────────
def _check_chaos() -> None:
    if os.getenv("CHAOS_MODE", "").strip() in ("1", "true", "TRUE", "yes"):
        raise RuntimeError("CHAOS_MODE on — forced LLM failure simulation")


# ─────────────────────────────────────────────────────────
# Day 7 — 단순 호출 (참고용, 데모는 chat_with_tools 사용)
# ─────────────────────────────────────────────────────────
def chat(user_message: str) -> str:
    """단순 호출 (Day 7 호환용, 도구 없이)"""
    _check_chaos()
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=400,
        extra_headers=EXTRA_HEADERS,
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────
# Day 8 — Tool Calling 본체 (회복력 wrapper 안에서만 호출)
# ─────────────────────────────────────────────────────────
def _chat_with_tools_live(user_message: str, max_tool_rounds: int = 3) -> dict:
    """
    Tool Calling 본체 — 네트워크/모델 호출만 담당. 예외는 그대로 위로 던짐.

    1. LLM 1차 호출 (tools 전달)
    2. tool_calls 반환 → 실제 함수 실행 → 결과 messages 추가 → LLM 재호출
    3. tool_calls 없으면 최종 응답 반환
    """
    _check_chaos()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    tools_called = []

    for round_num in range(max_tool_rounds + 1):
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0.3,
            max_tokens=600,
            extra_headers=EXTRA_HEADERS,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return {
                "reply": msg.content or "(empty response)",
                "tool_calls_made": tools_called,
                "rounds": round_num + 1,
            }

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = tc.function.arguments
            tools_called.append(tool_name)

            result = execute_tool(tool_name, tool_args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return {
        "reply": "(tool call limit exceeded — increase max_tool_rounds)",
        "tool_calls_made": tools_called,
        "rounds": max_tool_rounds + 1,
    }


# ─────────────────────────────────────────────────────────
# Day 9 — 회복력 wrapper (3·4단 폴백)
# ─────────────────────────────────────────────────────────
_GRACEFUL_REPLY = (
    "[Automatic fallback] The AI assistant is temporarily unavailable.\n"
    "You can still proceed with the standard incident response checklist below:\n\n"
    "1. Diagnose: review the most recent deployments and merged code changes.\n"
    "2. Check first: error-rate and latency dashboards for critical services, plus the on-call alert channel.\n"
    "3. Mitigate: consider rolling back the most recent suspect deployment, and review traffic-shifting or rate-limiting options.\n\n"
    "Once the AI is back online, the same question will return a full diagnosis automatically."
)


def chat_with_tools(user_message: str, max_tool_rounds: int = 3) -> dict:
    """
    회복력 wrapper — 라이브 호출 실패 시 캐시 → graceful 순으로 폴백.

    응답 dict 추가 필드:
        source: "live" | "cache" | "graceful"
        fallback_used: bool — 1차 라이브 호출 실패 여부
        fallback_reason: str | None — 실패 사유 (디버깅용)
        cache_age_seconds: int | None — 캐시 히트 시 응답 나이
        cache_stale: bool | None — TTL 초과 여부 (캐시 히트 시)
    """
    cache_key = cache.make_key(user_message)

    # 1차: 라이브 호출
    try:
        result = _chat_with_tools_live(user_message, max_tool_rounds)
        result["source"] = "live"
        result["fallback_used"] = False
        result["fallback_reason"] = None
        result["cache_age_seconds"] = None
        result["cache_stale"] = None

        # 성공한 응답만 캐시 (graceful 응답은 캐시하지 않음)
        try:
            cache.put(cache_key, result)
        except Exception:
            # 캐시 실패는 사용자 경험에 영향 X — 조용히 무시
            pass

        stats.record(result)
        return result

    except Exception as e:
        fallback_reason = f"{type(e).__name__}: {str(e)[:120]}"

        # 2차: 캐시 조회 (stale 도 OK — 최후 수단)
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None

        if cached is not None:
            cached["source"] = "cache"
            cached["fallback_used"] = True
            cached["fallback_reason"] = fallback_reason
            cached["cache_age_seconds"] = cached.pop("_cache_age_seconds", None)
            cached["cache_stale"] = cached.pop("_cache_stale", None)
            stats.record(cached)
            return cached

        # 3차: graceful 정적 응답
        result = {
            "reply": _GRACEFUL_REPLY,
            "tool_calls_made": [],
            "rounds": 0,
            "source": "graceful",
            "fallback_used": True,
            "fallback_reason": fallback_reason,
            "cache_age_seconds": None,
            "cache_stale": None,
        }
        stats.record(result)
        return result
