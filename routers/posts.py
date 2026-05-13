from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import httpx
from datetime import datetime, date

from auth_utils import verify_token, get_user_pages

router = APIRouter(tags=["posts"])

FB_API_BASE = "https://graph.facebook.com/v20.0"


def parse_fb_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str


def is_in_range(date_str: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> bool:
    if not date_str:
        return True
    try:
        post_date = date_str[:10]
        if date_from and post_date < date_from:
            return False
        if date_to and post_date > date_to:
            return False
        return True
    except Exception:
        return True


async def fetch_fb_posts(page_id: str, access_token: str, post_type: str, limit: int) -> list:
    posts = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        if post_type in ("published", "today"):
            # Fetch published posts
            url = f"{FB_API_BASE}/{page_id}/posts"
            params = {
                "access_token": access_token,
                "fields": "id,created_time,message",
                "limit": min(limit, 100),
            }
            resp = await client.get(url, params=params)
            data = resp.json()

            if "error" in data:
                raise HTTPException(status_code=400, detail=data["error"].get("message", "FB API error"))

            for post in data.get("data", []):
                posts.append({
                    "id":   post["id"],
                    "date": parse_fb_date(post.get("created_time")),
                    "type": "Published",
                    "raw_date": post.get("created_time", ""),
                })

        elif post_type == "scheduled":
            # Fetch scheduled posts
            url = f"{FB_API_BASE}/{page_id}/scheduled_posts"
            params = {
                "access_token": access_token,
                "fields": "id,scheduled_publish_time,message",
                "limit": min(limit, 100),
            }
            resp = await client.get(url, params=params)
            data = resp.json()

            if "error" in data:
                raise HTTPException(status_code=400, detail=data["error"].get("message", "FB API error"))

            for post in data.get("data", []):
                posts.append({
                    "id":   post["id"],
                    "date": parse_fb_date(post.get("scheduled_publish_time")),
                    "type": "Scheduled",
                    "raw_date": post.get("scheduled_publish_time", ""),
                })

    return posts


@router.get("/posts")
async def get_posts(
    type:  str           = Query("published", pattern="^(published|scheduled|today)$"),
    limit: int           = Query(50, ge=1, le=100),
    from_: Optional[str] = Query(None, alias="from"),
    to:    Optional[str] = Query(None),
    page_id: Optional[int] = Query(None, description="Specific FB page DB id (optional)"),
    current_user=Depends(verify_token),
):
    username = current_user["username"]
    pages    = get_user_pages(username)

    if not pages:
        raise HTTPException(status_code=404, detail="কোনো Facebook Page অ্যাক্সেস নেই")

    # Filter to specific page if requested
    if page_id:
        pages = [p for p in pages if p["id"] == page_id]
        if not pages:
            raise HTTPException(status_code=403, detail="এই page-এ অ্যাক্সেস নেই")

    today_str = date.today().isoformat()
    all_posts = []

    for page in pages:
        try:
            fetch_type = "published" if type == "today" else type
            posts = await fetch_fb_posts(page["page_id"], page["access_token"], fetch_type, limit)

            # Date filtering
            if type == "today":
                posts = [p for p in posts if p.get("raw_date", "")[:10] == today_str]
            else:
                posts = [p for p in posts if is_in_range(p.get("raw_date"), from_, to)]

            # Add page name to each post
            for p in posts:
                p["page_name"] = page["name"]
            all_posts.extend(posts)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Page '{page['name']}' লোড করতে সমস্যা: {str(e)}")

    # Sort by date descending
    all_posts.sort(key=lambda x: x.get("raw_date", ""), reverse=True)

    # Trim to limit
    all_posts = all_posts[:limit]

    # Remove raw_date from response
    for p in all_posts:
        p.pop("raw_date", None)

    return {"posts": all_posts, "total": len(all_posts)}


@router.get("/pages")
async def get_my_pages(current_user=Depends(verify_token)):
    pages = get_user_pages(current_user["username"])
    # Don't expose access tokens to frontend
    safe = [{"id": p["id"], "name": p["name"], "page_id": p["page_id"]} for p in pages]
    return {"pages": safe}
