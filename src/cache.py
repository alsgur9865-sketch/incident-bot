"""
cache.py — SQLite 기반 응답 캐시 (회복력 4단 체인의 3단계)

용도:
- LLM 호출 결과를 (질문 해시) → 응답 dict 로 저장
- 게이트웨이 + 모델 모두 실패 시 마지막 안전망

핵심 메타 아이러니:
"AI가 죽어도 사용자는 안 죽는다" — 캐시가 stale 이라도 graceful 메시지보다는 낫다.

테이블 스키마:
    responses(key TEXT PK, value TEXT, created_at REAL)
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

# 캐시 DB 경로 (incident-bot/cache/responses.db)
_CACHE_DIR = Path(__file__).parent.parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)
_DB_PATH = _CACHE_DIR / "responses.db"

# stale 판정 기준 (해커톤 데모는 stale 도 OK이므로 길게)
DEFAULT_TTL_SECONDS = 3600


def _get_conn() -> sqlite3.Connection:
    """DB 연결 + 테이블 생성 (없으면)"""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS responses (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    return conn


def make_key(message: str) -> str:
    """사용자 메시지 → 정규화된 캐시 키 (16자 SHA-256)"""
    normalized = message.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def get(key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict | None:
    """
    캐시 조회.

    Returns:
        None: 캐시 미스
        dict: 캐시 히트 (메타데이터 `_cache_age_seconds`, `_cache_stale` 포함)
              - stale 항목도 반환 (회복력 시나리오: 최후 수단)
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT value, created_at FROM responses WHERE key = ?",
            (key,),
        ).fetchone()

    if row is None:
        return None

    value_json, created_at = row
    age = time.time() - created_at
    data = json.loads(value_json)
    data["_cache_age_seconds"] = int(age)
    data["_cache_stale"] = age > ttl_seconds
    return data


def put(key: str, value: dict) -> None:
    """캐시 저장 (메타데이터 `_cache_*` 는 제외하고 저장)"""
    clean = {k: v for k, v in value.items() if not k.startswith("_cache_")}
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO responses (key, value, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(clean, ensure_ascii=False), time.time()),
        )
        conn.commit()


def stats() -> dict:
    """대시보드용 통계"""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        latest_row = conn.execute(
            "SELECT created_at FROM responses ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    latest_age = None
    if latest_row:
        latest_age = int(time.time() - latest_row[0])
    return {
        "total_entries": total,
        "latest_entry_age_seconds": latest_age,
        "db_path": str(_DB_PATH),
    }
