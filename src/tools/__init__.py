"""
tools/__init__.py — 모든 LLM Tool 의 통합 레지스트리

추가/제거 시 여기 한 곳만 손대면 LLM이 새 도구를 즉시 인지.

현재 등록된 도구:
- GitHub: get_recent_commits, get_recent_pulls (진짜 API)
- Sentry: sentry_get_recent_errors (mock)
- Logs:   logs_tail (mock)
"""

import json

from src.tools.github_tool import (
    TOOL_SCHEMAS as _GITHUB_SCHEMAS,
    TOOL_FUNCTIONS as _GITHUB_FUNCS,
)
from src.tools.sentry_tool import (
    TOOL_SCHEMA as _SENTRY_SCHEMA,
    get_recent_errors as _sentry_get_recent_errors,
)
from src.tools.logs_tool import (
    TOOL_SCHEMA as _LOGS_SCHEMA,
    tail_logs as _logs_tail,
)


# LLM에 넘길 전체 도구 스키마 목록
TOOL_SCHEMAS: list[dict] = [
    *_GITHUB_SCHEMAS,
    _SENTRY_SCHEMA,
    _LOGS_SCHEMA,
]

# tool 이름 → 실제 함수 매핑
TOOL_FUNCTIONS: dict[str, callable] = {
    **_GITHUB_FUNCS,
    "sentry_get_recent_errors": _sentry_get_recent_errors,
    "logs_tail": _logs_tail,
}


def execute_tool(name: str, arguments_json: str) -> str:
    """
    LLM이 요청한 tool 을 실제로 실행 (통합 디스패처).

    Args:
        name: tool 이름 (예: "get_recent_commits", "sentry_get_recent_errors")
        arguments_json: LLM이 보낸 인자 JSON 문자열

    Returns: tool 실행 결과 텍스트
    """
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return f"[ERROR] Unknown tool: {name}"

    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        args = {}

    try:
        return fn(**args)
    except TypeError as e:
        return f"[ERROR] Tool argument error ({name}): {e}"
    except Exception as e:
        return f"[ERROR] Tool execution failed ({name}): {type(e).__name__}: {e}"
