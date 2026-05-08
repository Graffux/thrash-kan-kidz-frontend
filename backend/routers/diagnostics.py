"""
Diagnostics router: admin viewers for crash logs.

Gated by a simple username query param (?user=Graffux) — not strong auth, but
prevents random scrapers from harvesting stack traces. Upgrade to JWT-gated
admin role post-launch if needed.
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
from motor.motor_asyncio import AsyncIOMotorClient

from series_config import (
    SERIES_CONFIG,
    persist_release_date,
    get_release_date,
    series_status,
    is_series_released,
)

router = APIRouter()

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]

# Hardcoded for v1. Move to env var when you onboard a second admin.
ADMIN_USERNAMES = {"Graffux"}


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )


@router.get("/admin/crashes")
async def list_crashes(user: str = "", limit: int = 50):
    """JSON crash log listing for programmatic access."""
    if user not in ADMIN_USERNAMES:
        raise HTTPException(status_code=403, detail="Forbidden")
    limit = max(1, min(limit, 500))
    crashes = (
        await db.crash_logs.find({}, {"_id": 0})
        .sort("received_at", -1)
        .to_list(limit)
    )
    # ISO-format any datetimes for JSON
    for c in crashes:
        rt = c.get("received_at")
        if rt and not isinstance(rt, str):
            c["received_at"] = rt.isoformat()
    return {"count": len(crashes), "crashes": crashes}


@router.get("/admin/crashes/view")
async def view_crashes_page(user: str = "", limit: int = 50):
    """
    Mobile-friendly HTML view of the most recent crashes.
    Open in your phone browser:
        {BACKEND_URL}/api/admin/crashes/view?user=Graffux
    """
    if user not in ADMIN_USERNAMES:
        return HTMLResponse(
            content="<h1 style='color:#fff;background:#000;padding:24px;font-family:Arial;'>403 Forbidden</h1>",
            status_code=403,
        )
    limit = max(1, min(limit, 500))
    crashes = (
        await db.crash_logs.find({}, {"_id": 0})
        .sort("received_at", -1)
        .to_list(limit)
    )

    rows = ""
    for c in crashes:
        received = c.get("received_at")
        received_str = (
            received.isoformat()[:19].replace("T", " ")
            if received and not isinstance(received, str)
            else (received or "")[:19].replace("T", " ")
        )
        err = _esc(c.get("error", ""))
        screen = _esc(c.get("screen", "-"))
        version = _esc(c.get("app_version", "-"))
        platform = _esc(c.get("platform", "-"))
        user_id = _esc(c.get("user_id") or "-")
        stack = _esc(c.get("stack", "") or "")[:1200]
        rows += f"""
        <div style="background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:14px;margin-bottom:10px;">
            <div style="color:#FFD700;font-size:11px;letter-spacing:1px;margin-bottom:4px;">{received_str}</div>
            <div style="color:#ff6b6b;font-weight:bold;margin-bottom:6px;font-size:14px;">{err}</div>
            <div style="color:#aaa;font-size:11px;margin-bottom:6px;">
                <b>screen:</b> {screen} &nbsp;
                <b>ver:</b> {version} &nbsp;
                <b>os:</b> {platform} &nbsp;
                <b>user:</b> {user_id}
            </div>
            <details style="color:#888;font-size:10px;">
                <summary style="cursor:pointer;color:#FFD700;">Stack</summary>
                <pre style="white-space:pre-wrap;word-break:break-word;background:#000;padding:8px;border-radius:6px;color:#bbb;margin-top:6px;">{stack}</pre>
            </details>
        </div>"""

    if not rows:
        rows = '<p style="color:#888;text-align:center;padding:40px;">No crashes logged. 🤘</p>'

    html = f"""<!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Thrash Kan Kidz — Crashes</title></head>
    <body style="background:#0f0f1a;color:#fff;font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:18px;">
    <h1 style="color:#FFD700;text-align:center;margin-bottom:4px;">💀 Crash Log</h1>
    <p style="color:#888;text-align:center;font-size:12px;margin-top:0;">Showing latest {len(crashes)} (max {limit})</p>
    {rows}
    </body></html>"""
    return HTMLResponse(content=html)



# ==========================================================================
# Series release scheduling — admin only
# ==========================================================================
# Lets you flip a "Coming Soon" series into "scheduled with a release date"
# (or the other way) at runtime, without redeploying. Persists in
# `db.series_overrides` so the change survives backend restarts.
# ==========================================================================

class SeriesReleaseDateBody(BaseModel):
    # ISO-8601 datetime string (UTC). Send `None`/null to clear and revert to
    # "Coming Soon".
    release_date: Optional[str] = None


@router.get("/admin/series/schedule")
async def get_series_schedule(user: str = ""):
    """Snapshot of every declared series + its current release status."""
    if user not in ADMIN_USERNAMES:
        raise HTTPException(status_code=403, detail="Forbidden")
    out = []
    for num in sorted(SERIES_CONFIG.keys()):
        cfg = SERIES_CONFIG[num]
        rel = get_release_date(num)
        out.append({
            "series": num,
            "name": cfg.get("name", f"Series {num}"),
            "description": cfg.get("description", ""),
            "status": series_status(num),
            "released": is_series_released(num),
            "release_date": rel.isoformat() if rel else None,
        })
    return {"series": out}


@router.post("/admin/series/{series_num}/release-date")
async def set_series_release_date(
    series_num: int,
    body: SeriesReleaseDateBody = Body(...),
    user: str = "",
):
    """
    Set or clear the release date for a series.

    Body:
        {"release_date": "2026-06-15T17:00:00Z"}   → schedule
        {"release_date": null}                      → clear (back to Coming Soon)

    The change takes effect immediately for this backend process AND any
    other replicas the next time they boot (the override is persisted in
    MongoDB and reloaded by `init_overrides()` on startup).
    """
    if user not in ADMIN_USERNAMES:
        raise HTTPException(status_code=403, detail="Forbidden")
    if series_num not in SERIES_CONFIG:
        raise HTTPException(status_code=404, detail="Unknown series")

    raw = body.release_date
    parsed: Optional[datetime] = None
    if raw is not None:
        # Accept "2026-06-15T17:00:00Z" or "2026-06-15T17:00:00+00:00".
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ISO datetime: {exc}",
            )
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

    await persist_release_date(db, series_num, parsed)

    return {
        "ok": True,
        "series": series_num,
        "release_date": parsed.isoformat() if parsed else None,
        "status": series_status(series_num),
        "released": is_series_released(series_num),
    }
