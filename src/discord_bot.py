"""
discord_bot.py — Discord 봇 (Day 12)

영상 1·2컷 ("자다 깬 1인 개발자, 폰 알람 → Discord 봇 1차 진단") 의 진입점.
회복력 wrapper가 백엔드에 있어서 봇 자체에는 안전망 박을 필요 없음.

슬래시 명령:
- /incident <message>  : 인시던트 진단 요청 (source별 색상 embed)
- /chaos <on|off|toggle>: 카오스 토글 (영상 4컷)
- /stats               : 회복력 통계 (영상 6컷)

전제:
- .env 에 DISCORD_TOKEN 설정 (필수)
- 선택: DISCORD_GUILD_ID 설정 시 즉시 sync, 없으면 글로벌 (반영 1시간)
- FastAPI 서버가 http://localhost:8000 에 떠 있어야 함

실행:
    powershell -ExecutionPolicy Bypass -File D:\\project\\devpost_hackton\\incident-bot\\bot.ps1
"""

import os

import discord
import httpx
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")  # optional
API_BASE = "http://localhost:8000"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────────────────
# API 헬퍼 (FastAPI 백엔드 호출 — async)
# ─────────────────────────────────────────────────────────
async def api_post(path: str, json_body: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{API_BASE}{path}", json=json_body)
        r.raise_for_status()
        return r.json()


async def api_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{API_BASE}{path}")
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────────────────
# Embed 빌더 — source별 색상 분기 (영상 시각화)
# ─────────────────────────────────────────────────────────
def _color_for(source: str) -> discord.Color:
    return {
        "live": discord.Color.green(),
        "cache": discord.Color.gold(),
        "graceful": discord.Color.red(),
    }.get(source, discord.Color.blurple())


def _emoji_for(source: str) -> str:
    return {"live": "✅", "cache": "♻️", "graceful": "💥"}.get(source, "❔")


def build_incident_embed(message: str, result: dict) -> discord.Embed:
    source = result.get("source", "live")

    embed = discord.Embed(
        title=f"{_emoji_for(source)} Incident Diagnosis",
        description=(result.get("reply") or "(empty response)")[:4000],
        color=_color_for(source),
    )

    embed.add_field(name="📝 Query", value=message[:1024], inline=False)
    embed.add_field(name="source", value=f"`{source}`", inline=True)
    embed.add_field(name="rounds", value=str(result.get("rounds", 0)), inline=True)

    tools = result.get("tool_calls_made", [])
    if tools:
        embed.add_field(
            name="🛠 Tools Used",
            value=" ".join(f"`{t}`" for t in tools),
            inline=False,
        )

    if source == "cache":
        age = result.get("cache_age_seconds")
        stale = result.get("cache_stale")
        embed.add_field(
            name="cache",
            value=f"{age}s ago ({'stale' if stale else 'fresh'})",
            inline=True,
        )

    if result.get("fallback_used"):
        embed.add_field(
            name="⚠️ Fallback Reason",
            value=f"`{(result.get('fallback_reason') or '?')[:200]}`",
            inline=False,
        )

    embed.set_footer(
        text="Incident Response Bot · TrueFoundry Resilient Agents Challenge"
    )
    return embed


# ─────────────────────────────────────────────────────────
# 이벤트
# ─────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[Discord] Logged in as {bot.user} (id={bot.user.id})")
    # 진단: 봇이 실제로 들어간 서버 목록
    print(f"[Discord] DISCORD_GUILD_ID in .env = {DISCORD_GUILD_ID!r}")
    print(f"[Discord] Bot is IN these guilds:")
    for g in bot.guilds:
        match = " <-- MATCH" if str(g.id) == str(DISCORD_GUILD_ID) else ""
        print(f"           id={g.id}  name={g.name!r}{match}")
    if not bot.guilds:
        print("           (none — bot is not in any server!)")

    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"[Discord] Guild-synced {len(synced)} commands (instant)")
        else:
            synced = await bot.tree.sync()
            print(
                f"[Discord] Global-synced {len(synced)} commands "
                f"(propagation up to 1h)"
            )
    except Exception as e:
        print(f"[Discord] Sync failed: {e}")


# ─────────────────────────────────────────────────────────
# 슬래시 커맨드
# ─────────────────────────────────────────────────────────
@bot.tree.command(name="incident", description="Request incident diagnosis (uses resilience wrapper)")
@app_commands.describe(message="Describe the situation (e.g., api-gateway is throwing 503)")
async def incident(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    try:
        result = await api_post("/chat/tools", {"message": message})
        embed = build_incident_embed(message, result)
        await interaction.followup.send(embed=embed)
    except httpx.HTTPError as e:
        await interaction.followup.send(
            f"❌ FastAPI server call failed: `{e}`\n"
            f"Make sure the server is running via `start.ps1`."
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Bot internal error: `{type(e).__name__}: {e}`")


@bot.tree.command(name="chaos", description="Toggle LLM forced failure mode (chaos demo)")
@app_commands.describe(action="on / off / toggle")
@app_commands.choices(
    action=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
        app_commands.Choice(name="toggle", value="toggle"),
    ]
)
async def chaos(
    interaction: discord.Interaction, action: app_commands.Choice[str]
):
    await interaction.response.defer(thinking=True)
    body: dict = {}
    if action.value == "on":
        body = {"on": True}
    elif action.value == "off":
        body = {"on": False}
    try:
        result = await api_post("/chaos/toggle", body)
        chaos_on = result.get("chaos_mode", False)
        emoji = "🔥" if chaos_on else "✅"
        await interaction.followup.send(
            f"{emoji} **CHAOS_MODE = {chaos_on}** "
            f"(prev: `{result.get('previous')}`, changed: `{result.get('changed')}`)"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Bot call failed: `{e}`")


@bot.tree.command(name="stats", description="Resilience statistics")
async def stats(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        s = await api_get("/stats")
        bs = s.get("by_source", {})
        embed = discord.Embed(
            title="📊 Resilience Stats",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Total Requests",
            value=f"`{s.get('total_requests', 0)}`",
            inline=True,
        )
        embed.add_field(
            name="User Dropped",
            value=f"`{s.get('user_dropped_count', 0)}`  ⭐",
            inline=True,
        )
        embed.add_field(
            name="​",  # spacer
            value="​",
            inline=True,
        )
        embed.add_field(name="✅ Live", value=str(bs.get("live", 0)), inline=True)
        embed.add_field(name="♻️ Cache", value=str(bs.get("cache", 0)), inline=True)
        embed.add_field(
            name="💥 Graceful", value=str(bs.get("graceful", 0)), inline=True
        )
        embed.add_field(
            name="rates",
            value=(
                f"fallback `{s.get('fallback_rate', 0)*100:.1f}%` · "
                f"cache hit `{s.get('cache_hit_rate', 0)*100:.1f}%` · "
                f"graceful `{s.get('graceful_rate', 0)*100:.1f}%`"
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"uptime {s.get('uptime_seconds', 0)}s · "
            f"TrueFoundry Resilient Agents Challenge"
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Bot call failed: `{e}`")


# ─────────────────────────────────────────────────────────
# 엔트리포인트
# ─────────────────────────────────────────────────────────
def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN environment variable is missing. "
            "Add 'DISCORD_TOKEN=...' to .env and rerun."
        )
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
