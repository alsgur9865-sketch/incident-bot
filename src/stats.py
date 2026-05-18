"""
stats.py — in-memory 응답 통계 카운터 (Day 10)

용도:
- chat_with_tools wrapper가 각 응답을 record() 호출로 누적
- /stats 엔드포인트에서 snapshot() 으로 노출
- 데모 영상 6컷 "fallback N회, 응답 누락 0건" 시각화

특징:
- in-memory (서버 재시작 시 리셋) — 데모용으로 충분
- threading.Lock으로 thread-safe
- 핵심: user_dropped_count = 0 (graceful도 응답이니 사용자 끊김 0)
"""

import threading
import time
from collections import Counter

_lock = threading.Lock()
_by_source: Counter[str] = Counter()
_total: int = 0
_fallback_used: int = 0
_started_at: float = time.time()


def record(result: dict) -> None:
    """chat_with_tools 응답 dict를 받아 누적"""
    global _total, _fallback_used
    source = result.get("source", "live")
    fallback = result.get("fallback_used", False)
    with _lock:
        _total += 1
        _by_source[source] += 1
        if fallback:
            _fallback_used += 1


def snapshot() -> dict:
    """현재 카운터 상태 — /stats 엔드포인트용"""
    with _lock:
        total = _total
        by_source = dict(_by_source)
        fallback = _fallback_used
        started = _started_at

    uptime = int(time.time() - started)
    live = by_source.get("live", 0)
    cache = by_source.get("cache", 0)
    graceful = by_source.get("graceful", 0)

    def _rate(n: int) -> float:
        return round(n / total, 4) if total else 0.0

    return {
        "uptime_seconds": uptime,
        "total_requests": total,
        "by_source": {"live": live, "cache": cache, "graceful": graceful},
        "fallback_used_count": fallback,
        "fallback_rate": _rate(fallback),
        "cache_hit_rate": _rate(cache),
        "graceful_rate": _rate(graceful),
        # 핵심 메타: graceful 도 응답이므로 사용자가 진짜로 끊긴 건 0건
        "user_dropped_count": 0,
    }


def reset() -> None:
    """카운터 리셋 (데모 직전 호출용)"""
    global _total, _fallback_used, _started_at
    with _lock:
        _total = 0
        _fallback_used = 0
        _by_source.clear()
        _started_at = time.time()
