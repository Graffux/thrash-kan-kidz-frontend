"""
Mosh Pit — lightweight social feed where players post text updates and
react to each other. Self-contained router (uses the shared Mongo client).

Endpoints:
  POST   /api/mosh/posts                 → create a post
  GET    /api/mosh/feed?limit=20         → latest posts (newest first)
  GET    /api/mosh/posts/{post_id}       → single post
  POST   /api/mosh/posts/{post_id}/react → toggle 💀 reaction (per user)
  DELETE /api/mosh/posts/{post_id}       → delete own post

Data model (`db.mosh_posts`):
  {
    id: str (uuid),
    user_id: str,
    username: str,         # denormalized for cheap feed reads
    content: str,
    created_at: ISO string,
    reactors: list[str],   # user_ids who 💀'd it (toggle list)
  }
"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid

router = APIRouter()

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]

MAX_CONTENT_LEN = 200
MAX_COMMENT_LEN = 200
MAX_IMAGE_BYTES = 1_500_000  # ~1.5MB base64 (Mongo doc safe size)


def _serialize(post: dict, viewer_id: str | None = None) -> dict:
    """Strip Mongo internals + add viewer-specific reaction flag."""
    reactors = post.get("reactors") or []
    return {
        "id": post["id"],
        "user_id": post["user_id"],
        "username": post.get("username", "anon"),
        "content": post.get("content", ""),
        "image": post.get("image"),  # base64 data URI or None
        "created_at": post.get("created_at"),
        "reaction_count": len(reactors),
        "viewer_reacted": viewer_id in reactors if viewer_id else False,
        "comment_count": int(post.get("comment_count", 0)),
    }


def _serialize_comment(c: dict, viewer_id: str | None = None) -> dict:
    reactors = c.get("reactors") or []
    return {
        "id": c["id"],
        "post_id": c["post_id"],
        "user_id": c["user_id"],
        "username": c.get("username", "anon"),
        "content": c.get("content", ""),
        "created_at": c.get("created_at"),
        "reaction_count": len(reactors),
        "viewer_reacted": viewer_id in reactors if viewer_id else False,
    }


@router.post("/mosh/posts")
async def create_post(request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    content = (body.get("content") or "").strip()
    image = body.get("image")  # optional base64 data URI
    if not user_id:
        raise HTTPException(400, "user_id required")
    if not content and not image:
        raise HTTPException(400, "Post needs text or an image")
    if content and len(content) > MAX_CONTENT_LEN:
        raise HTTPException(400, f"Post too long (max {MAX_CONTENT_LEN} chars)")
    if image:
        if not isinstance(image, str) or not image.startswith("data:image/"):
            raise HTTPException(400, "image must be a data:image/...;base64 URI")
        # Reject anything larger than the cap before it hits Mongo's 16MB doc limit.
        if len(image) > MAX_IMAGE_BYTES:
            raise HTTPException(400, "Image too large (max ~1MB after encoding)")

    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    post = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "username": user.get("username", "anon"),
        "content": content,
        "image": image,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reactors": [],
        "comment_count": 0,
    }
    await db.mosh_posts.insert_one(post)
    return _serialize(post, viewer_id=user_id)


@router.get("/mosh/feed")
async def get_feed(limit: int = 20, viewer_id: str | None = None):
    limit = max(1, min(limit, 100))
    cursor = db.mosh_posts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    posts = await cursor.to_list(limit)
    return [_serialize(p, viewer_id=viewer_id) for p in posts]


@router.get("/mosh/posts/{post_id}")
async def get_post(post_id: str, viewer_id: str | None = None):
    post = await db.mosh_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Post not found")
    return _serialize(post, viewer_id=viewer_id)


@router.post("/mosh/posts/{post_id}/react")
async def toggle_reaction(post_id: str, request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id required")

    post = await db.mosh_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(404, "Post not found")

    reactors = post.get("reactors") or []
    if user_id in reactors:
        reactors.remove(user_id)
    else:
        reactors.append(user_id)
    await db.mosh_posts.update_one(
        {"id": post_id},
        {"$set": {"reactors": reactors}},
    )
    updated = await db.mosh_posts.find_one({"id": post_id}, {"_id": 0})
    return _serialize(updated, viewer_id=user_id)


@router.delete("/mosh/posts/{post_id}")
async def delete_post(post_id: str, request: Request):
    # Body-based auth (matches the rest of the app's patterns).
    body = await request.json()
    user_id = body.get("user_id")
    post = await db.mosh_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(404, "Post not found")
    if post["user_id"] != user_id:
        raise HTTPException(403, "Can only delete your own posts")
    await db.mosh_posts.delete_one({"id": post_id})
    # Cascade delete comments
    await db.mosh_comments.delete_many({"post_id": post_id})
    return {"success": True}


# ─── Comments ────────────────────────────────────────────────────────────
# Flat one-level threads: every comment attaches to a post_id, no nesting.

@router.get("/mosh/posts/{post_id}/comments")
async def list_comments(post_id: str, limit: int = 100, viewer_id: str | None = None):
    limit = max(1, min(limit, 500))
    cursor = db.mosh_comments.find(
        {"post_id": post_id}, {"_id": 0}
    ).sort("created_at", 1).limit(limit)
    return [_serialize_comment(c, viewer_id=viewer_id) for c in await cursor.to_list(limit)]


@router.post("/mosh/comments/{comment_id}/react")
async def react_comment(comment_id: str, request: Request):
    """Toggle a 💀 reaction on a comment.

    Mirrors the post-level /react endpoint: idempotent toggle keyed by user_id.
    Stored as a list of user_ids in `reactors` on the comment doc — same shape
    as posts so future analytics can union the two collections easily.
    """
    body = await request.json()
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id required")
    comment = await db.mosh_comments.find_one({"id": comment_id})
    if not comment:
        raise HTTPException(404, "Comment not found")
    reactors = comment.get("reactors") or []
    if user_id in reactors:
        # Un-react (toggle off)
        await db.mosh_comments.update_one(
            {"id": comment_id}, {"$pull": {"reactors": user_id}}
        )
        reactors = [u for u in reactors if u != user_id]
    else:
        # React (toggle on) — $addToSet keeps it idempotent on retries.
        await db.mosh_comments.update_one(
            {"id": comment_id}, {"$addToSet": {"reactors": user_id}}
        )
        reactors = reactors + [user_id]
    return {
        "id": comment_id,
        "reaction_count": len(reactors),
        "viewer_reacted": user_id in reactors,
    }


@router.post("/mosh/posts/{post_id}/comments")
async def create_comment(post_id: str, request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    content = (body.get("content") or "").strip()
    if not user_id:
        raise HTTPException(400, "user_id required")
    if not content:
        raise HTTPException(400, "Comment can't be empty")
    if len(content) > MAX_COMMENT_LEN:
        raise HTTPException(400, f"Comment too long (max {MAX_COMMENT_LEN} chars)")

    post = await db.mosh_posts.find_one({"id": post_id})
    if not post:
        raise HTTPException(404, "Post not found")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    comment = {
        "id": str(uuid.uuid4()),
        "post_id": post_id,
        "user_id": user_id,
        "username": user.get("username", "anon"),
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.mosh_comments.insert_one(comment)
    await db.mosh_posts.update_one({"id": post_id}, {"$inc": {"comment_count": 1}})
    return _serialize_comment(comment)


@router.delete("/mosh/comments/{comment_id}")
async def delete_comment(comment_id: str, request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    comment = await db.mosh_comments.find_one({"id": comment_id})
    if not comment:
        raise HTTPException(404, "Comment not found")
    if comment["user_id"] != user_id:
        raise HTTPException(403, "Can only delete your own comments")
    await db.mosh_comments.delete_one({"id": comment_id})
    await db.mosh_posts.update_one(
        {"id": comment["post_id"]},
        {"$inc": {"comment_count": -1}},
    )
    return {"success": True}
