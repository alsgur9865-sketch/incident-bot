"""
dashboard.py — Streamlit 대시보드 (Day 13 디자인 리뉴얼)

영상 시연 + 데모용 UI — SaaS 제품 룩앤필.
"""

from datetime import datetime

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Incident Response Bot — TrueFoundry Resilient Agents",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────
# 글로벌 CSS (영상 임팩트용)
# ─────────────────────────────────────────────────────────
CSS = """
<style>
/* 기본 폰트 시스템 */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 "Helvetica Neue", Arial, sans-serif;
}

/* Streamlit 기본 헤더/푸터 제거 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {display: none;}
.block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; max-width: 1280px;}

/* Hero 헤더 */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #312e81 100%);
    border-radius: 16px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.hero h1 {
    color: white;
    margin: 0 0 6px 0;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
}
.hero .subtitle {
    color: #cbd5e1;
    font-size: 15px;
    margin: 0;
}
.hero .meta-tagline {
    margin-top: 14px;
    padding: 10px 14px;
    background: rgba(99, 102, 241, 0.2);
    border-left: 3px solid #818cf8;
    border-radius: 6px;
    font-size: 14px;
    color: #e0e7ff;
}

/* 상태 배지 */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.badge-ok    { background: #10b981; color: white; }
.badge-chaos { background: #ef4444; color: white; animation: pulse 1.5s infinite; }
@keyframes pulse {
    0%,100% { opacity: 1; }
    50%     { opacity: 0.6; }
}

/* CHAOS 빨간 풀폭 배너 */
.chaos-banner {
    background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%);
    color: white;
    padding: 14px 20px;
    border-radius: 12px;
    text-align: center;
    font-weight: 600;
    font-size: 15px;
    box-shadow: 0 6px 18px rgba(220, 38, 38, 0.35);
    margin: 0 0 20px 0;
    border: 2px solid #fca5a5;
}

/* 응답 카드 (source 별 색) */
.response-card {
    border-radius: 12px;
    padding: 20px 22px;
    margin-top: 12px;
    border: 1px solid rgba(0,0,0,0.06);
    background: white;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.response-card.live     { border-left: 6px solid #10b981; }
.response-card.cache    { border-left: 6px solid #f59e0b; }
.response-card.graceful { border-left: 6px solid #ef4444; }

.source-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.source-pill.live     { background: #d1fae5; color: #065f46; }
.source-pill.cache    { background: #fef3c7; color: #92400e; }
.source-pill.graceful { background: #fee2e2; color: #991b1b; }

.tool-chip {
    display: inline-block;
    padding: 4px 10px;
    margin: 3px 4px 3px 0;
    border-radius: 6px;
    background: #ede9fe;
    color: #5b21b6;
    font-size: 12px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
}

/* KPI 큰 숫자 카드 */
.kpi-card {
    border-radius: 14px;
    padding: 18px 20px;
    background: white;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.kpi-card.hero-metric {
    background: linear-gradient(135deg, #065f46 0%, #10b981 100%);
    color: white;
    border: none;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.kpi-card.hero-metric .kpi-label { color: rgba(255,255,255,0.85); }
.kpi-value {
    font-size: 36px;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.03em;
    color: #111827;
}
.kpi-card.hero-metric .kpi-value { color: white; }
.kpi-sub {
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
}
.kpi-card.hero-metric .kpi-sub { color: rgba(255,255,255,0.85); }

/* 소형 KPI grid */
.mini-kpi {
    background: #f9fafb;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    border: 1px solid #e5e7eb;
}
.mini-kpi .num { font-size: 22px; font-weight: 700; color: #111827; }
.mini-kpi .lbl { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px;}

/* Section 헤딩 */
.section-title {
    font-size: 13px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 4px 0 10px 0;
}

/* 챌린지 인용구 */
.challenge-quote {
    background: #f8fafc;
    border-left: 4px solid #6366f1;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    color: #334155;
    font-size: 13px;
    font-style: italic;
    margin-bottom: 18px;
}

/* 푸터 */
.footer-strip {
    margin-top: 32px;
    padding: 14px 0;
    border-top: 1px solid #e5e7eb;
    font-size: 12px;
    color: #6b7280;
    text-align: center;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []


# ─────────────────────────────────────────────────────────
# API 헬퍼
# ─────────────────────────────────────────────────────────
def api_get(path: str) -> dict:
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def api_post(path: str, json_body: dict | None = None) -> dict:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=json_body, timeout=60.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────
# Hero 헤더
# ─────────────────────────────────────────────────────────
health = api_get("/")
if "_error" in health:
    st.error("⚠️ 서버가 응답하지 않습니다. `start.ps1` 로 서버를 띄우세요.")
    st.code(health["_error"])
    st.stop()

chaos_on = health.get("chaos_mode", False)
chaos_badge = (
    '<span class="badge badge-chaos">🔥 CHAOS ON</span>'
    if chaos_on
    else '<span class="badge badge-ok">● HEALTHY</span>'
)

st.markdown(
    f"""
<div class="hero">
  <h1>🚨 Incident Response Bot &nbsp; {chaos_badge}</h1>
  <p class="subtitle">
    Resilient DevOps agent · TrueFoundry AI Gateway · 4-layer fallback chain ·
    <code style="color:#a5b4fc;">v{health.get('version','?')}</code>
  </p>
  <div class="meta-tagline">
    💡 <strong>"When the AI dies, the user doesn't."</strong>
    &nbsp;The agent survives total infrastructure chaos through
    Groq → Gemini → SQLite cache → graceful fallback.
    The headline metric: <code>user_dropped_count: 0</code>.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# 챌린지 인용구 (영상 첫 화면에 노출)
st.markdown(
    """
<div class="challenge-quote">
  📜 <strong>TrueFoundry Resilient Agents Challenge brief</strong>:
  "How does your agent behave when an MCP server starts erroring out?
   An LLM server goes down? OpenAI or Claude errors out or browns out?
   The goal is to see how user experience and the user side of things are
   handled when this infrastructure chaos happens."
</div>
""",
    unsafe_allow_html=True,
)

# CHAOS 빨간 풀폭 배너 (영상 4컷 핵심 시각)
if chaos_on:
    st.markdown(
        '<div class="chaos-banner">🔥 &nbsp; CHAOS MODE ON &nbsp; · &nbsp; '
        'All LLM calls are forced to fail · '
        'Resilience fallback (cache / graceful) is active</div>',
        unsafe_allow_html=True,
    )

# 헤더 우측 토글
col_a, col_b = st.columns([5, 1])
with col_a:
    pass
with col_b:
    if chaos_on:
        if st.button("✅ Turn CHAOS OFF", type="secondary", use_container_width=True):
            api_post("/chaos/toggle", {"on": False})
            st.rerun()
    else:
        if st.button("💀 Kill the AI (Chaos)", type="primary", use_container_width=True):
            api_post("/chaos/toggle", {"on": True})
            st.rerun()


# ─────────────────────────────────────────────────────────
# 메인 — 좌 입력 + 응답 / 우 통계
# ─────────────────────────────────────────────────────────
main_left, main_right = st.columns([2, 1])

with main_left:
    st.markdown('<div class="section-title">📣 Report an incident</div>', unsafe_allow_html=True)

    presets = {
        "(custom — type your own)": "",
        "Sentry + Logs combined diagnosis": "api-gateway is throwing 503 errors, check sentry and logs",
        "Recent code changes": "check recent commits",
        "Redis OOM-kill loop": "my redis cluster keeps OOM-killing",
    }
    preset_choice = st.selectbox("Preset", list(presets.keys()))
    default_msg = presets.get(preset_choice, "")

    with st.form("incident_form", clear_on_submit=False):
        msg = st.text_area(
            "Incident description",
            value=default_msg,
            placeholder="e.g. api-gateway is throwing 503 errors",
            height=100,
        )
        submitted = st.form_submit_button(
            "🚀 Diagnose", type="primary", use_container_width=True
        )

    if submitted and msg.strip():
        with st.spinner("Calling LLM (resilience wrapper handles fallback)…"):
            result = api_post("/chat/tools", {"message": msg.strip()})
        if "_error" not in result:
            st.session_state.history.insert(
                0,
                {
                    "ts": datetime.now().strftime("%H:%M:%S"),
                    "msg": msg.strip(),
                    "result": result,
                },
            )
        else:
            st.error(f"호출 실패: {result['_error']}")

    # 최신 응답 카드
    if st.session_state.history:
        latest = st.session_state.history[0]
        r = latest["result"]
        source = r.get("source", "live")

        meta_html = (
            f'<span class="source-pill {source}">{source}</span>'
            f' &nbsp;·&nbsp; <strong>rounds:</strong> {r.get("rounds", 0)}'
        )
        if source == "cache":
            age = r.get("cache_age_seconds", 0)
            meta_html += f' &nbsp;·&nbsp; <strong>cache age:</strong> {age}s'
        if r.get("fallback_used"):
            reason = (r.get("fallback_reason") or "?")[:80]
            meta_html += f'<br><span style="color:#dc2626; font-size:12px;">⚠️ fallback: <code>{reason}</code></span>'

        tools = r.get("tool_calls_made") or []
        tool_html = ""
        if tools:
            chips = "".join(f'<span class="tool-chip">{t}</span>' for t in tools)
            tool_html = f'<div style="margin-top:10px;">🛠 <strong>tools called:</strong> {chips}</div>'

        reply = (r.get("reply") or "(empty response)").replace("\n", "<br>")

        st.markdown(
            f"""
<div class="response-card {source}">
  <div style="display:flex; justify-content:space-between; align-items:start;">
    <div style="flex:1;">{meta_html}</div>
  </div>
  {tool_html}
  <hr style="margin:14px 0; border:none; border-top:1px solid #e5e7eb;">
  <div style="font-size:14px; line-height:1.6; color:#1f2937;">{reply}</div>
</div>
""",
            unsafe_allow_html=True,
        )

with main_right:
    st.markdown('<div class="section-title">📊 Resilience Stats</div>', unsafe_allow_html=True)

    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    if btn_col2.button("🧹 Reset", use_container_width=True):
        api_post("/stats/reset")
        st.session_state.history = []
        st.rerun()

    stats = api_get("/stats")
    cache_stats = api_get("/cache/stats")

    if "_error" not in stats:
        # HERO METRIC — 영상 6컷의 단 한 줄
        dropped = stats.get("user_dropped_count", 0)
        st.markdown(
            f"""
<div class="kpi-card hero-metric" style="margin-bottom:14px;">
  <div class="kpi-label">User Dropped</div>
  <div class="kpi-value">{dropped}</div>
  <div class="kpi-sub">graceful counts as a response · zero true drops</div>
</div>
""",
            unsafe_allow_html=True,
        )

        bs = stats.get("by_source", {})
        st.markdown(
            f"""
<div class="kpi-card" style="margin-bottom:14px;">
  <div class="kpi-label">Total requests</div>
  <div class="kpi-value">{stats.get('total_requests', 0)}</div>
</div>

<div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:8px; margin-bottom:14px;">
  <div class="mini-kpi" style="border-left:4px solid #10b981;">
    <div class="num">{bs.get('live', 0)}</div>
    <div class="lbl">Live</div>
  </div>
  <div class="mini-kpi" style="border-left:4px solid #f59e0b;">
    <div class="num">{bs.get('cache', 0)}</div>
    <div class="lbl">Cache</div>
  </div>
  <div class="mini-kpi" style="border-left:4px solid #ef4444;">
    <div class="num">{bs.get('graceful', 0)}</div>
    <div class="lbl">Graceful</div>
  </div>
</div>

<div class="kpi-card">
  <div style="font-size:12px; color:#6b7280; line-height:1.8;">
    <strong>fallback rate</strong> &nbsp; <code>{stats.get('fallback_rate', 0)*100:.1f}%</code><br>
    <strong>cache hit rate</strong> &nbsp; <code>{stats.get('cache_hit_rate', 0)*100:.1f}%</code><br>
    <strong>graceful rate</strong> &nbsp; <code>{stats.get('graceful_rate', 0)*100:.1f}%</code><br>
    <strong>uptime</strong> &nbsp; <code>{stats.get('uptime_seconds', 0)}s</code>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        if cache_stats and "_error" not in cache_stats:
            st.caption(
                f"💾 SQLite cache: **{cache_stats.get('total_entries', 0)}** entries"
            )


# ─────────────────────────────────────────────────────────
# 호출 히스토리
# ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title" style="margin-top:32px;">📜 Call History</div>', unsafe_allow_html=True)

if not st.session_state.history:
    st.info("아직 호출 기록 없음. 위에서 인시던트 메시지를 보내보세요.")
else:
    for i, item in enumerate(st.session_state.history[:10]):
        r = item["result"]
        source = r.get("source", "live")
        emoji = {"live": "🟢", "cache": "🟡", "graceful": "🔴"}.get(source, "⚪")
        with st.expander(
            f"{emoji}  [{item['ts']}]  {source.upper()}  ·  {item['msg'][:70]}",
            expanded=(i == 0),
        ):
            cols = st.columns(4)
            cols[0].metric("source", source)
            cols[1].metric("rounds", r.get("rounds", 0))
            cols[2].metric("tools", len(r.get("tool_calls_made") or []))
            age = r.get("cache_age_seconds")
            cols[3].metric("cache age", f"{age}s" if age is not None else "—")
            tools = r.get("tool_calls_made") or []
            if tools:
                st.markdown(
                    "🛠 " + " ".join(f'<span class="tool-chip">{t}</span>' for t in tools),
                    unsafe_allow_html=True,
                )
            st.markdown("---")
            st.markdown(r.get("reply", "(빈 응답)"))


# ─────────────────────────────────────────────────────────
# 푸터
# ─────────────────────────────────────────────────────────
st.markdown(
    """
<div class="footer-strip">
  🏆 <strong>DevNetwork [AI + ML] Hackathon 2026</strong> &nbsp;·&nbsp;
  TrueFoundry Resilient Agents Challenge &nbsp;·&nbsp;
  4-layer chain: Groq → Gemini → SQLite cache → Graceful
</div>
""",
    unsafe_allow_html=True,
)
