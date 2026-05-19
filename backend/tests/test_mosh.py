"""Integration tests for the Mosh Pit community feed (/api/mosh/*)."""
import os
import requests

API = os.environ.get("TEST_API_URL", "http://localhost:8001")
USER_ID = "0b820bda-18e5-4ca9-9ba1-e493617a23e3"


def test_create_post_and_appear_in_feed():
    res = requests.post(
        f"{API}/api/mosh/posts",
        json={"user_id": USER_ID, "content": "pytest hello mosh"},
        timeout=60,
    )
    assert res.status_code == 200
    post = res.json()
    pid = post["id"]
    assert post["content"] == "pytest hello mosh"
    assert post["username"] == "Graffux"
    assert post["reaction_count"] == 0

    feed = requests.get(f"{API}/api/mosh/feed?limit=5", timeout=15).json()
    assert any(p["id"] == pid for p in feed)

    # Cleanup
    requests.delete(
        f"{API}/api/mosh/posts/{pid}",
        json={"user_id": USER_ID}, timeout=15,
    )


def test_empty_content_rejected():
    res = requests.post(
        f"{API}/api/mosh/posts",
        json={"user_id": USER_ID, "content": "   "},
        timeout=15,
    )
    assert res.status_code == 400


def test_too_long_content_rejected():
    res = requests.post(
        f"{API}/api/mosh/posts",
        json={"user_id": USER_ID, "content": "a" * 500},
        timeout=15,
    )
    assert res.status_code == 400


def test_reaction_toggle():
    # Create a post to react to
    create = requests.post(
        f"{API}/api/mosh/posts",
        json={"user_id": USER_ID, "content": "react-me"}, timeout=15,
    ).json()
    pid = create["id"]
    try:
        r1 = requests.post(
            f"{API}/api/mosh/posts/{pid}/react",
            json={"user_id": USER_ID}, timeout=15,
        ).json()
        assert r1["reaction_count"] == 1
        assert r1["viewer_reacted"] is True

        r2 = requests.post(
            f"{API}/api/mosh/posts/{pid}/react",
            json={"user_id": USER_ID}, timeout=15,
        ).json()
        assert r2["reaction_count"] == 0
        assert r2["viewer_reacted"] is False
    finally:
        requests.delete(
            f"{API}/api/mosh/posts/{pid}",
            json={"user_id": USER_ID}, timeout=15,
        )


def test_delete_others_post_forbidden():
    create = requests.post(
        f"{API}/api/mosh/posts",
        json={"user_id": USER_ID, "content": "do not delete me"}, timeout=15,
    ).json()
    pid = create["id"]
    try:
        res = requests.delete(
            f"{API}/api/mosh/posts/{pid}",
            json={"user_id": "some-other-user-id"}, timeout=15,
        )
        assert res.status_code == 403
    finally:
        requests.delete(
            f"{API}/api/mosh/posts/{pid}",
            json={"user_id": USER_ID}, timeout=15,
        )


def test_404_on_missing_post():
    res = requests.post(
        f"{API}/api/mosh/posts/this-id-does-not-exist/react",
        json={"user_id": USER_ID}, timeout=15,
    )
    assert res.status_code == 404


def test_feed_no_leaks():
    """Posts should NEVER expose Mongo _id or other internals."""
    feed = requests.get(f"{API}/api/mosh/feed?limit=5", timeout=15).json()
    allowed = {"id", "user_id", "username", "content", "created_at",
               "reaction_count", "viewer_reacted"}
    for p in feed:
        assert set(p.keys()) == allowed, f"Unexpected keys: {set(p.keys()) - allowed}"
