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


# ---------------------------------------------------------------------------
# MOSH PIT CLEANUP — one-click keyword pruning of outdated announcements.
# Open in any browser (or your phone) and click through:
#   {BACKEND_URL}/api/admin/mosh/cleanup/view?user=Graffux
#
# Two-step flow on purpose:
#   1. ?keyword=...        → preview matches (no deletion)
#   2. ?keyword=...&confirm=1 → actually deletes posts + their nested comments
# ---------------------------------------------------------------------------
@router.get("/admin/mosh/cleanup")
async def mosh_cleanup_json(
    user: str = "",
    keyword: str = "",
    confirm: int = 0,
):
    """JSON variant for scripting / curl. See /admin/mosh/cleanup/view for UI."""
    if user not in ADMIN_USERNAMES:
        raise HTTPException(status_code=403, detail="Forbidden")
    keyword = (keyword or "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword required")

    # Case-insensitive substring match on `content`.
    query = {"content": {"$regex": keyword, "$options": "i"}}
    matches = await db.mosh_posts.find(
        query, {"_id": 0, "id": 1, "username": 1, "content": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(500)

    if not confirm:
        return {
            "dry_run": True,
            "keyword": keyword,
            "match_count": len(matches),
            "matches": matches,
            "hint": "Re-call with &confirm=1 to actually delete.",
        }

    # Confirmed delete — also drop nested comments to keep collections clean.
    match_ids = [m["id"] for m in matches]
    posts_res = await db.mosh_posts.delete_many({"id": {"$in": match_ids}})
    comments_res = await db.mosh_comments.delete_many({"post_id": {"$in": match_ids}})
    return {
        "dry_run": False,
        "keyword": keyword,
        "deleted_posts": posts_res.deleted_count,
        "deleted_comments": comments_res.deleted_count,
        "removed_ids": match_ids,
    }


@router.get("/admin/mosh/cleanup/view", response_class=HTMLResponse)
async def mosh_cleanup_view(user: str = "", keyword: str = "", confirm: int = 0):
    """
    Mobile-friendly HTML page. Open in your browser:
        {BACKEND_URL}/api/admin/mosh/cleanup/view?user=Graffux
    Then type a keyword → preview → click DELETE to confirm.
    """
    if user not in ADMIN_USERNAMES:
        return HTMLResponse(
            "<h1>403 Forbidden</h1><p>Pass ?user=&lt;admin username&gt;</p>",
            status_code=403,
        )

    keyword = (keyword or "").strip()
    deleted_summary = ""
    matches: list[dict] = []
    confirmed = bool(confirm) and bool(keyword)

    if confirmed:
        query = {"content": {"$regex": keyword, "$options": "i"}}
        targets = await db.mosh_posts.find(query, {"_id": 0, "id": 1}).to_list(500)
        target_ids = [t["id"] for t in targets]
        posts_res = await db.mosh_posts.delete_many({"id": {"$in": target_ids}})
        comments_res = await db.mosh_comments.delete_many(
            {"post_id": {"$in": target_ids}}
        )
        deleted_summary = (
            f"<div style='background:#1e3a1e;border:1px solid #3a7a3a;"
            f"padding:12px;border-radius:8px;margin:12px 0;color:#9fe39f;'>"
            f"✅ Deleted <b>{posts_res.deleted_count}</b> post(s) and "
            f"<b>{comments_res.deleted_count}</b> nested comment(s) "
            f"matching <code>{_esc(keyword)}</code>."
            f"</div>"
        )
        # After delete, run a fresh search to show "no remaining matches"
        matches = await db.mosh_posts.find(
            {"content": {"$regex": keyword, "$options": "i"}},
            {"_id": 0, "id": 1, "username": 1, "content": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(50)
    elif keyword:
        matches = await db.mosh_posts.find(
            {"content": {"$regex": keyword, "$options": "i"}},
            {"_id": 0, "id": 1, "username": 1, "content": 1, "created_at": 1},
        ).sort("created_at", -1).to_list(50)

    # Render the matches table
    rows_html = ""
    for m in matches:
        ts = m.get("created_at", "")
        if not isinstance(ts, str):
            ts = ts.isoformat() if ts else ""
        rows_html += (
            f"<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #333;'>"
            f"<code style='color:#888;font-size:11px;'>{_esc(m.get('id',''))[:8]}…</code>"
            f"</td>"
            f"<td style='padding:8px;border-bottom:1px solid #333;color:#ffd24a;'>"
            f"{_esc(m.get('username',''))}"
            f"</td>"
            f"<td style='padding:8px;border-bottom:1px solid #333;'>"
            f"{_esc(m.get('content','')[:180])}"
            f"</td>"
            f"</tr>"
        )
    table_html = (
        f"<table style='width:100%;border-collapse:collapse;background:#161616;"
        f"color:#eee;font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:13px;'>"
        f"<thead><tr style='background:#222;'>"
        f"<th style='padding:8px;text-align:left;'>ID</th>"
        f"<th style='padding:8px;text-align:left;'>User</th>"
        f"<th style='padding:8px;text-align:left;'>Content</th>"
        f"</tr></thead><tbody>{rows_html or '<tr><td colspan=3 style=padding:20px;color:#666;>No posts matched.</td></tr>'}</tbody></table>"
    ) if keyword else ""

    delete_btn = ""
    if matches and keyword and not confirmed:
        delete_btn = (
            f"<form method='get' style='margin-top:16px;'>"
            f"<input type='hidden' name='user' value='{_esc(user)}'>"
            f"<input type='hidden' name='keyword' value='{_esc(keyword)}'>"
            f"<input type='hidden' name='confirm' value='1'>"
            f"<button type='submit' style='background:#a02828;color:#fff;"
            f"padding:12px 24px;border:none;border-radius:6px;font-size:16px;"
            f"font-weight:bold;cursor:pointer;' "
            f"onclick=\"return confirm('Permanently delete {len(matches)} post(s) matching &quot;{_esc(keyword)}&quot;?');\">"
            f"🗑️  DELETE {len(matches)} POST(S)"
            f"</button>"
            f"</form>"
        )

    page = f"""
    <!doctype html>
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Mosh Pit Cleanup</title></head>
    <body style="background:#0d0d0d;color:#eee;font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;max-width:900px;margin:0 auto;">
    <h1 style="color:#ffd24a;border-bottom:2px solid #444;padding-bottom:8px;">🤘 Mosh Pit Cleanup</h1>
    <p style="color:#aaa;">Search posts by keyword (case-insensitive). Preview, then confirm to delete.</p>

    <form method="get" style="background:#1a1a1a;padding:16px;border-radius:8px;border:1px solid #333;">
      <input type="hidden" name="user" value="{_esc(user)}">
      <label style="display:block;margin-bottom:8px;color:#bbb;font-size:14px;">Keyword:</label>
      <input type="text" name="keyword" value="{_esc(keyword)}" placeholder="e.g. coming soon" autofocus
        style="width:100%;padding:10px;background:#222;color:#fff;border:1px solid #444;border-radius:6px;font-size:16px;box-sizing:border-box;">
      <button type="submit" style="margin-top:12px;background:#3a7a3a;color:#fff;padding:10px 20px;border:none;border-radius:6px;font-size:15px;cursor:pointer;">
        🔍 Preview Matches
      </button>
    </form>

    {deleted_summary}

    {f'<h2 style="color:#ffd24a;margin-top:24px;">Matches for &ldquo;{_esc(keyword)}&rdquo; ({len(matches)})</h2>' if keyword else ''}
    {table_html}
    {delete_btn}

    <p style="color:#555;font-size:11px;margin-top:32px;border-top:1px solid #222;padding-top:12px;">
    Logged in as <code style="color:#ffd24a;">{_esc(user)}</code>.
    Also available as JSON: <code>/api/admin/mosh/cleanup?user={_esc(user)}&keyword=…&confirm=1</code>
    </p>
    </body></html>
    """
    return HTMLResponse(page)
