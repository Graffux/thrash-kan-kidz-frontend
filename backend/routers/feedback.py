"""
Feedback endpoints: collect and view tester feedback.
Fully self-contained (only depends on the shared Mongo `db`).
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter()

# Reuse the same mongo connection. Using the same env vars as server.py so
# both modules share the same logical database.
_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]


@router.post("/feedback")
async def submit_feedback(request: Request):
    """Submit user feedback."""
    body = await request.json()
    user_id = body.get("user_id", "")
    username = body.get("username", "")
    rating = body.get("rating", 0)
    message = body.get("message", "")
    if not message.strip():
        raise HTTPException(status_code=400, detail="Feedback message is required")
    feedback = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "username": username,
        "rating": rating,
        "message": message.strip(),
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.feedback.insert_one(feedback)
    return {"success": True, "message": "Thank you for your feedback!"}


@router.get("/feedback")
async def get_all_feedback():
    """Get all feedback (admin)."""
    feedback_list = (
        await db.feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    )
    return feedback_list


@router.get("/feedback/view")
async def view_feedback_page():
    """View feedback as a nice HTML page."""
    feedback_list = (
        await db.feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    )
    stars_html = ""
    for f in feedback_list:
        rating = f.get("rating", 0)
        stars = "\u2605" * rating + "\u2606" * (5 - rating)
        message = (
            f.get("message", "")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        stars_html += f"""
        <div style="background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:16px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <strong style="color:#FFD700;font-size:16px;">{f.get('username','Anonymous')}</strong>
                <span style="color:#FFD700;font-size:18px;">{stars}</span>
            </div>
            <p style="color:#ddd;margin:8px 0;font-size:14px;">{message}</p>
            <small style="color:#666;">{f.get('created_at','')[:16]}</small>
        </div>"""

    html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Thrash Kan Kidz - Feedback</title></head>
    <body style="background:#0f0f1a;color:#fff;font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
    <h1 style="color:#FFD700;text-align:center;">Tester Feedback</h1>
    <p style="color:#888;text-align:center;">{len(feedback_list)} responses</p>
    {stars_html}
    </body></html>"""
    return HTMLResponse(content=html)
