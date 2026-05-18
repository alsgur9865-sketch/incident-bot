"""
github_tool.py — GitHub API 호출 함수 + LLM Tool 스키마

목적:
- 인시던트 봇이 LLM Tool Calling으로 호출할 수 있는 GitHub 조회 함수
- Day 9에서 TrueFoundry MCP Gateway로 승격 예정 (지금은 직접 호출)

함수:
- get_recent_commits(limit): 최근 커밋 N개
- get_recent_pulls(limit, state): 최근 PR N개
"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    """GitHub API 인증 헤더"""
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN and not GITHUB_TOKEN.startswith("ghp_your"):
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def get_recent_commits(limit: int = 5) -> str:
    """
    설정된 repo의 최근 커밋을 조회.

    Returns: LLM에 넘기기 좋은 텍스트 요약 (SHA, 메시지, 작성자, 시각)
    """
    if not GITHUB_REPO:
        return "[ERROR] GITHUB_REPO environment variable is missing"

    limit = max(1, min(int(limit), 10))
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/commits"

    try:
        resp = httpx.get(
            url,
            headers=_headers(),
            params={"per_page": limit},
            timeout=10.0,
        )
        resp.raise_for_status()
        commits = resp.json()
    except httpx.HTTPStatusError as e:
        return f"[ERROR] GitHub API error {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"[ERROR] GitHub call failed: {type(e).__name__}: {e}"

    if not commits:
        return f"[INFO] No recent commits in {GITHUB_REPO}"

    lines = [f"=== Recent commits: {len(commits)} ({GITHUB_REPO}) ==="]
    for c in commits:
        sha = c["sha"][:7]
        msg = c["commit"]["message"].split("\n")[0][:80]
        author = c["commit"]["author"]["name"]
        date = c["commit"]["author"]["date"]
        lines.append(f"- {sha} | {date} | {author}: {msg}")
    return "\n".join(lines)


def get_recent_pulls(limit: int = 5, state: str = "all") -> str:
    """
    설정된 repo의 최근 PR을 조회.

    Args:
        limit: 1~10개
        state: "open", "closed", "all" 중 하나

    Returns: LLM 친화 텍스트 요약
    """
    if not GITHUB_REPO:
        return "[ERROR] GITHUB_REPO environment variable is missing"

    limit = max(1, min(int(limit), 10))
    if state not in {"open", "closed", "all"}:
        state = "all"

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/pulls"

    try:
        resp = httpx.get(
            url,
            headers=_headers(),
            params={"per_page": limit, "state": state, "sort": "updated", "direction": "desc"},
            timeout=10.0,
        )
        resp.raise_for_status()
        pulls = resp.json()
    except httpx.HTTPStatusError as e:
        return f"[ERROR] GitHub API error {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return f"[ERROR] GitHub call failed: {type(e).__name__}: {e}"

    if not pulls:
        return f"[INFO] No {state} PRs in {GITHUB_REPO}"

    lines = [f"=== Recent PRs: {len(pulls)} ({GITHUB_REPO}, state={state}) ==="]
    for p in pulls:
        num = p["number"]
        title = p["title"][:80]
        state_str = p["state"]
        user = p["user"]["login"]
        updated = p["updated_at"]
        lines.append(f"- #{num} [{state_str}] {updated} by {user}: {title}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# LLM Tool 스키마 (OpenAI/Groq function calling 형식)
# ─────────────────────────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_commits",
            "description": (
                "Fetch the most recent commits from the configured GitHub repository. "
                "Call this when diagnosing an incident to see 'what changed recently'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of commits to fetch (1-10)",
                        "default": 5,
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_pulls",
            "description": (
                "Fetch the most recent pull requests from the configured GitHub repository. "
                "Call this to inspect upcoming or recently merged changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of PRs to fetch (1-10)",
                        "default": 5,
                    },
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter by PR state",
                        "default": "all",
                    },
                },
            },
        },
    },
]


# tool name → 실제 함수 매핑
TOOL_FUNCTIONS = {
    "get_recent_commits": get_recent_commits,
    "get_recent_pulls": get_recent_pulls,
}


def execute_tool(name: str, arguments_json: str) -> str:
    """
    LLM이 요청한 tool을 실제로 실행한다.

    Args:
        name: tool 이름 (예: "get_recent_commits")
        arguments_json: LLM이 보낸 인자 JSON 문자열

    Returns: tool 실행 결과 텍스트 (LLM이 다시 받아 종합 응답에 사용)
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
