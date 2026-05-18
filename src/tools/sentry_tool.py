"""
sentry_tool.py — Mock Sentry MCP 도구 (Day 10)

Sentry 진짜 API 대신 결정적(deterministic) 가짜 데이터 반환.
영상 시연용 — "AI가 여러 도구를 조합해서 인시던트 진단" 컷.

Day 14+ TrueFoundry MCP Gateway 정식 통합 시 이 파일만 갈아끼우면 끝
(시그니처/스키마 유지).
"""

import json
from datetime import datetime, timedelta


# 결정적 시드 데이터 — 데모 일관성을 위해 고정
_MOCK_ERRORS = [
    {
        "id": "ERR-7821",
        "level": "error",
        "title": "DatabaseTimeoutError: query exceeded 5000ms",
        "service": "api-gateway",
        "count_last_hour": 142,
        "first_seen_minutes_ago": 18,
        "fingerprint": "db-query-timeout",
    },
    {
        "id": "ERR-7822",
        "level": "warning",
        "title": "ConnectionPoolExhausted: max=50 in_use=50",
        "service": "api-gateway",
        "count_last_hour": 87,
        "first_seen_minutes_ago": 22,
        "fingerprint": "pool-exhausted",
    },
    {
        "id": "ERR-7820",
        "level": "error",
        "title": "PaymentService 504 Gateway Timeout",
        "service": "checkout",
        "count_last_hour": 31,
        "first_seen_minutes_ago": 14,
        "fingerprint": "checkout-timeout",
    },
]


def get_recent_errors(service: str = "all", limit: int = 5) -> str:
    """
    최근 1시간 내 Sentry 에러 조회 (mock).

    Args:
        service: "all" 또는 서비스명 ("api-gateway", "checkout" 등)
        limit: 1~10개

    Returns: LLM 친화 텍스트
    """
    limit = max(1, min(int(limit), 10))

    errors = _MOCK_ERRORS
    if service and service != "all":
        errors = [e for e in errors if e["service"] == service]

    if not errors:
        return f"[Sentry mock] No recent errors for service '{service}'"

    errors = errors[:limit]
    lines = [f"=== Sentry recent errors: {len(errors)} (service={service}) ==="]
    for e in errors:
        lines.append(
            f"- {e['id']} [{e['level']}] {e['service']}: {e['title']} "
            f"(last 1h: {e['count_last_hour']} occurrences, first seen {e['first_seen_minutes_ago']} min ago)"
        )
    return "\n".join(lines)


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "sentry_get_recent_errors",
        "description": (
            "Fetch errors reported to Sentry in the last hour. "
            "Call this during incident diagnosis to see which errors are surging."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to filter ('all' or e.g. 'api-gateway', 'checkout')",
                    "default": "all",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of errors to fetch (1-10)",
                    "default": 5,
                },
            },
        },
    },
}
