"""
logs_tool.py — Mock Logs (Datadog/Loki) MCP 도구 (Day 10)

가짜 로그 라인 반환 — 영상 시연 + Sentry 도구와 조합 진단.
"""


_MOCK_LOG_LINES = [
    "[2026-05-18T20:11:42Z] INFO  api-gateway: request received GET /v1/orders",
    "[2026-05-18T20:11:43Z] WARN  api-gateway: db pool wait=2400ms threshold=1000ms",
    "[2026-05-18T20:11:47Z] ERROR api-gateway: DatabaseTimeoutError after 5012ms",
    "[2026-05-18T20:11:48Z] INFO  api-gateway: retry 1/3 for query",
    "[2026-05-18T20:11:53Z] ERROR api-gateway: DatabaseTimeoutError after 5008ms",
    "[2026-05-18T20:11:54Z] INFO  api-gateway: retry 2/3 for query",
    "[2026-05-18T20:11:59Z] ERROR api-gateway: DatabaseTimeoutError after 5011ms",
    "[2026-05-18T20:12:00Z] ERROR api-gateway: 503 Service Unavailable returned to client",
    "[2026-05-18T20:12:01Z] WARN  api-gateway: ConnectionPoolExhausted max=50 in_use=50",
    "[2026-05-18T20:12:05Z] INFO  api-gateway: circuit breaker OPEN for db.primary",
]


def tail_logs(service: str = "api-gateway", lines: int = 10) -> str:
    """
    서비스별 최근 로그 N줄 (mock).

    Args:
        service: 서비스명
        lines: 1~50줄
    """
    lines = max(1, min(int(lines), 50))
    tail = _MOCK_LOG_LINES[-lines:]
    header = f"=== Logs tail {len(tail)} lines (service={service}) ==="
    return header + "\n" + "\n".join(tail)


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "logs_tail",
        "description": (
            "Fetch recent log lines for a given service. "
            "Call this when you need more detailed context (stack, preceding actions) around a Sentry error."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name (e.g. 'api-gateway', 'checkout')",
                    "default": "api-gateway",
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of tail lines (1-50)",
                    "default": 10,
                },
            },
        },
    },
}
