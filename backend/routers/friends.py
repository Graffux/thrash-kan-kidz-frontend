"""
Friends system endpoints: send/accept/reject friend requests and list friends.
Self-contained (only depends on the shared Mongo `db`).
"""
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter()

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]


@router.post("/friends/request")
async def send_friend_request(request: Request):
    """Send a friend request."""
    body = await request.json()
    from_user_id = body.get("from_user_id")
    to_user_id = body.get("to_user_id")

    if from_user_id == to_user_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a friend")

    from_user = await db.users.find_one({"id": from_user_id})
    to_user = await db.users.find_one({"id": to_user_id})
    if not from_user or not to_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_friend = await db.friends.find_one({
        "$or": [
            {"user_id": from_user_id, "friend_id": to_user_id},
            {"user_id": to_user_id, "friend_id": from_user_id},
        ]
    })
    if existing_friend:
        raise HTTPException(status_code=400, detail="Already friends")

    existing_request = await db.friend_requests.find_one({
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "status": "pending",
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="Friend request already sent")

    reverse_request = await db.friend_requests.find_one({
        "from_user_id": to_user_id,
        "to_user_id": from_user_id,
        "status": "pending",
    })
    if reverse_request:
        await db.friend_requests.update_one(
            {"id": reverse_request["id"]},
            {"$set": {"status": "accepted"}},
        )
        await db.friends.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": from_user_id,
            "friend_id": to_user_id,
            "created_at": datetime.utcnow().isoformat(),
        })
        return {"success": True, "message": "You are now friends!", "auto_accepted": True}

    friend_req = {
        "id": str(uuid.uuid4()),
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "from_username": from_user.get("username", ""),
        "to_username": to_user.get("username", ""),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.friend_requests.insert_one(friend_req)
    return {"success": True, "message": "Friend request sent!"}


@router.post("/friends/accept/{request_id}")
async def accept_friend_request(request_id: str):
    """Accept a friend request."""
    freq = await db.friend_requests.find_one({"id": request_id, "status": "pending"})
    if not freq:
        raise HTTPException(status_code=404, detail="Friend request not found")

    await db.friend_requests.update_one(
        {"id": request_id}, {"$set": {"status": "accepted"}}
    )

    await db.friends.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": freq["from_user_id"],
        "friend_id": freq["to_user_id"],
        "created_at": datetime.utcnow().isoformat(),
    })

    return {"success": True, "message": "Friend request accepted!"}


@router.post("/friends/reject/{request_id}")
async def reject_friend_request(request_id: str):
    """Reject a friend request."""
    freq = await db.friend_requests.find_one({"id": request_id, "status": "pending"})
    if not freq:
        raise HTTPException(status_code=404, detail="Friend request not found")

    await db.friend_requests.update_one(
        {"id": request_id}, {"$set": {"status": "rejected"}}
    )
    return {"success": True, "message": "Friend request rejected"}


@router.get("/friends/{user_id}")
async def get_friends(user_id: str):
    """Get user's friends list with friend counts."""
    friends = await db.friends.find(
        {"$or": [{"user_id": user_id}, {"friend_id": user_id}]},
        {"_id": 0},
    ).to_list(500)

    friend_ids = []
    for f in friends:
        friend_ids.append(
            f["friend_id"] if f["user_id"] == user_id else f["user_id"]
        )

    friends_data = []
    for fid in friend_ids:
        friend_user = await db.users.find_one(
            {"id": fid}, {"_id": 0, "password_hash": 0}
        )
        if friend_user:
            friend_count = await db.friends.count_documents({
                "$or": [{"user_id": fid}, {"friend_id": fid}]
            })
            friend_user["friend_count"] = friend_count
            friends_data.append(friend_user)

    return {"friends": friends_data, "count": len(friends_data)}


@router.get("/friends/{user_id}/requests")
async def get_friend_requests(user_id: str):
    """Get pending friend requests for a user."""
    incoming = await db.friend_requests.find(
        {"to_user_id": user_id, "status": "pending"}, {"_id": 0}
    ).to_list(100)

    outgoing = await db.friend_requests.find(
        {"from_user_id": user_id, "status": "pending"}, {"_id": 0}
    ).to_list(100)

    return {"incoming": incoming, "outgoing": outgoing}
