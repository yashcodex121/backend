import re
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)

# In-memory rooms and sid->user mapping
rooms: Dict[str, Dict[str, Any]] = {}
sid_to_session: Dict[str, Dict[str, Any]] = {}

ROOM_DEFAULTS = {
    "cinema": {
        "title": "Interstellar - Official Trailer (4K Experience)",
        "url": "https://www.youtube.com/watch?v=zSWdZVtXT7E",
        "type": "youtube",
        "bgVideo": "https://files.catbox.moe/p7rxvf.jpg",
    },
    "music": {
        "title": "Lo-Fi Chill Hip Hop Beats - 24/7 Relaxing Music",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "type": "youtube",
        "bgVideo": "https://files.catbox.moe/ovqzpz.jpg",
    },
    "vip": {
        "title": "Top Hits & Movie Trailers Showcase",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "type": "youtube",
        "bgVideo": "https://files.catbox.moe/le9jny.jpg",
    },
    "chill": {
        "title": "Cozy Rain & Fireplace Chill Vibes",
        "url": "https://www.youtube.com/watch?v=mPZkdNFkNps",
        "type": "youtube",
        "bgVideo": "https://files.catbox.moe/p7rxvf.jpg",
    },
}


def detect_media_type(url: Optional[str]) -> str:
    if not url:
        return "youtube"
    clean = url.strip().lower()
    if "youtube.com" in clean or "youtu.be" in clean:
        return "youtube"
    if re.search(r"\.(mp4|webm|mkv|mov)(\?.*)?$", clean):
        return "video"
    if re.search(r"\.(mp3|wav|ogg|aac|m4a)(\?.*)?$", clean):
        return "audio"
    return "youtube"


def now_ms() -> int:
    return int(time.time() * 1000)


def formatted_time() -> str:
    return datetime.now().strftime("%I:%M %p").lstrip("0")


def get_estimated_current_time(media: Dict[str, Any]) -> float:
    if media.get("state") == "playing":
        elapsed = (now_ms() - media.get("updatedAt", now_ms())) / 1000.0
        return float(media.get("currentTime", 0)) + max(0.0, elapsed)
    return float(media.get("currentTime", 0))


def get_or_create_room(room_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    if room_id not in rooms:
        room_type = options.get("roomType") or "cinema"
        preset = ROOM_DEFAULTS.get(room_type, ROOM_DEFAULTS["cinema"])
        bg_url = (options.get("bgVideoUrl") or "").strip() or preset["bgVideo"]
        rooms[room_id] = {
            "id": room_id,
            "name": options.get("roomName") or f"Room {room_id[:6]}",
            "type": room_type,
            "bgVideoUrl": bg_url,
            "users": {},
            "media": {
                "url": preset["url"],
                "type": preset["type"],
                "title": preset["title"],
                "state": "paused",
                "currentTime": 0,
                "updatedAt": now_ms(),
            },
            "queue": [
                {
                    "id": "q1",
                    "title": "Aesthetic Chill Synthwave Stream",
                    "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY",
                    "type": "youtube",
                    "mediaType": "youtube",
                    "addedBy": "System",
                },
                {
                    "id": "q2",
                    "title": "Big Buck Bunny (HD Open Cinema)",
                    "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                    "type": "video",
                    "mediaType": "video",
                    "addedBy": "System",
                },
            ],
            "chat": [],
        }
    return rooms[room_id]


@sio.event
async def connect(sid, environ):
    pass


@sio.on("join-room")
async def on_join_room(sid, data):
    data = data or {}
    room_id = (data.get("roomId") or "").strip()
    if not room_id:
        return

    room = get_or_create_room(room_id, data)
    existing_admins = [u for u in room["users"].values() if u.get("isAdmin")]
    make_admin = bool(data.get("makeAdmin")) or len(existing_admins) == 0

    username = (data.get("username") or "").strip() or f"User_{sid[:4]}"
    current_user = {
        "socketId": sid,
        "username": username,
        "isAdmin": bool(make_admin),
        "joinedAt": now_ms(),
    }

    room["users"][sid] = current_user
    sid_to_session[sid] = {"roomId": room_id, "user": current_user}
    await sio.enter_room(sid, room_id)

    bg_video_url = (data.get("bgVideoUrl") or "").strip()
    if bg_video_url and not room.get("bgVideoUrl"):
        room["bgVideoUrl"] = bg_video_url

    await sio.emit(
        "room-joined",
        {
            "room": {
                "id": room["id"],
                "name": room["name"],
                "type": room["type"],
                "bgVideoUrl": room["bgVideoUrl"],
                "media": {
                    **room["media"],
                    "estimatedTime": get_estimated_current_time(room["media"]),
                },
                "queue": room["queue"],
                "users": list(room["users"].values()),
                "chat": room["chat"],
            },
            "me": current_user,
        },
        to=sid,
    )

    await sio.emit("user-list-updated", list(room["users"].values()), room=room_id)

    role_label = "👑 Co-Admin" if current_user["isAdmin"] else "👤 Viewer"
    join_msg = {
        "id": f"sys_{now_ms()}",
        "sender": "System",
        "isSystem": True,
        "text": f"{current_user['username']} joined the room as {role_label}",
        "time": formatted_time(),
    }
    room["chat"].append(join_msg)
    if len(room["chat"]) > 100:
        room["chat"].pop(0)
    await sio.emit("new-chat-message", join_msg, room=room_id)


@sio.on("admin-play")
async def on_admin_play(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    current_time = (data or {}).get("currentTime") or 0
    room["media"]["state"] = "playing"
    room["media"]["currentTime"] = current_time
    room["media"]["updatedAt"] = now_ms()

    await sio.emit(
        "media-played",
        {"currentTime": room["media"]["currentTime"], "by": user["username"]},
        room=sess["roomId"],
    )


@sio.on("admin-pause")
async def on_admin_pause(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    current_time = (data or {}).get("currentTime") or 0
    room["media"]["state"] = "paused"
    room["media"]["currentTime"] = current_time
    room["media"]["updatedAt"] = now_ms()

    await sio.emit(
        "media-paused",
        {"currentTime": room["media"]["currentTime"], "by": user["username"]},
        room=sess["roomId"],
    )


@sio.on("admin-seek")
async def on_admin_seek(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    current_time = (data or {}).get("currentTime") or 0
    room["media"]["currentTime"] = current_time
    room["media"]["updatedAt"] = now_ms()

    await sio.emit(
        "media-seeked",
        {"currentTime": room["media"]["currentTime"], "by": user["username"]},
        room=sess["roomId"],
    )


@sio.on("admin-change-media")
async def on_admin_change_media(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    data = data or {}
    url = (data.get("url") or "").strip()
    if not url:
        return
    detected_type = data.get("mediaType") or detect_media_type(url)
    title = data.get("title") or ("Audio Track" if detected_type == "audio" else "Video / Movie")

    room["media"] = {
        "url": url,
        "type": detected_type,
        "title": title,
        "state": "playing",
        "currentTime": 0,
        "updatedAt": now_ms(),
    }

    await sio.emit(
        "media-changed",
        {"media": room["media"], "by": user["username"]},
        room=sess["roomId"],
    )

    sys_msg = {
        "id": f"sys_{now_ms()}",
        "sender": "System",
        "isSystem": True,
        "text": f'👑 Admin {user["username"]} loaded: "{room["media"]["title"]}"',
        "time": formatted_time(),
    }
    room["chat"].append(sys_msg)
    if len(room["chat"]) > 100:
        room["chat"].pop(0)
    await sio.emit("new-chat-message", sys_msg, room=sess["roomId"])


@sio.on("admin-toggle-role")
async def on_admin_toggle_role(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    target_sid = (data or {}).get("targetSocketId")
    target_user = room["users"].get(target_sid)
    if target_user:
        target_user["isAdmin"] = not target_user["isAdmin"]
        await sio.emit("role-updated", {"isAdmin": target_user["isAdmin"]}, to=target_sid)
        await sio.emit("user-list-updated", list(room["users"].values()), room=sess["roomId"])

        role_text = "promoted to 👑 Co-Admin" if target_user["isAdmin"] else "now a 👤 Viewer"
        msg = {
            "id": f"sys_{now_ms()}",
            "sender": "System",
            "isSystem": True,
            "text": f"{target_user['username']} is {role_text} by {user['username']}",
            "time": formatted_time(),
        }
        room["chat"].append(msg)
        if len(room["chat"]) > 100:
            room["chat"].pop(0)
        await sio.emit("new-chat-message", msg, room=sess["roomId"])


@sio.on("admin-update-bg")
async def on_admin_update_bg(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    bg_url = ((data or {}).get("bgVideoUrl") or "").strip()
    if bg_url:
        room["bgVideoUrl"] = bg_url
        await sio.emit(
            "bg-video-updated",
            {"bgVideoUrl": room["bgVideoUrl"], "by": user["username"]},
            room=sess["roomId"],
        )
        sys_msg = {
            "id": f"sys_{now_ms()}",
            "sender": "System",
            "isSystem": True,
            "text": f"🎨 Theme background updated by 👑 {user['username']}",
            "time": formatted_time(),
        }
        room["chat"].append(sys_msg)
        if len(room["chat"]) > 100:
            room["chat"].pop(0)
        await sio.emit("new-chat-message", sys_msg, room=sess["roomId"])


@sio.on("add-to-queue")
async def on_add_to_queue(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room:
        return

    data = data or {}
    url = (data.get("url") or "").strip()
    if not url:
        return
    detected_type = data.get("mediaType") or detect_media_type(url)
    item = {
        "id": f"q_{now_ms()}_{uuid.uuid4().hex[:4]}",
        "url": url,
        "type": detected_type,
        "mediaType": detected_type,
        "title": data.get("title") or ("Custom Music" if detected_type == "audio" else "Custom Movie/Video"),
        "addedBy": user["username"] if user else "Guest",
    }
    room["queue"].append(item)
    await sio.emit("queue-updated", room["queue"], room=sess["roomId"])


@sio.on("play-from-queue")
async def on_play_from_queue(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    item_id = (data or {}).get("itemId")
    idx = next((i for i, item in enumerate(room["queue"]) if item["id"] == item_id), -1)
    if idx != -1:
        item = room["queue"].pop(idx)
        room["media"] = {
            "url": item["url"],
            "type": item["type"],
            "title": item["title"],
            "state": "playing",
            "currentTime": 0,
            "updatedAt": now_ms(),
        }
        await sio.emit("media-changed", {"media": room["media"], "by": user["username"]}, room=sess["roomId"])
        await sio.emit("queue-updated", room["queue"], room=sess["roomId"])


@sio.on("remove-from-queue")
async def on_remove_from_queue(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    if not room or not user.get("isAdmin"):
        return

    item_id = (data or {}).get("itemId")
    room["queue"] = [i for i in room["queue"] if i["id"] != item_id]
    await sio.emit("queue-updated", room["queue"], room=sess["roomId"])


@sio.on("send-chat")
async def on_send_chat(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    user = sess["user"]
    text = ((data or {}).get("text") or "").strip()
    if not room or not user or not text:
        return

    chat_msg = {
        "id": f"msg_{now_ms()}",
        "sender": user["username"],
        "isAdmin": user["isAdmin"],
        "isSystem": False,
        "text": text[:300],
        "time": formatted_time(),
    }
    room["chat"].append(chat_msg)
    if len(room["chat"]) > 100:
        room["chat"].pop(0)
    await sio.emit("new-chat-message", chat_msg, room=sess["roomId"])


@sio.on("send-reaction")
async def on_send_reaction(sid, data):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    user = sess["user"]
    emoji = (data or {}).get("emoji")
    if not emoji:
        return
    await sio.emit(
        "new-reaction",
        {"emoji": emoji, "from": user["username"]},
        room=sess["roomId"],
    )


@sio.on("request-sync")
async def on_request_sync(sid):
    sess = sid_to_session.get(sid)
    if not sess:
        return
    room = rooms.get(sess["roomId"])
    if not room:
        return
    await sio.emit(
        "sync-state",
        {
            "state": room["media"]["state"],
            "estimatedTime": get_estimated_current_time(room["media"]),
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    sess = sid_to_session.pop(sid, None)
    if not sess:
        return
    room_id = sess["roomId"]
    room = rooms.get(room_id)
    if not room:
        return

    departed = room["users"].pop(sid, None)
    if not departed:
        return

    await sio.emit("user-list-updated", list(room["users"].values()), room=room_id)

    if room["users"]:
        sys_msg = {
            "id": f"sys_{now_ms()}",
            "sender": "System",
            "isSystem": True,
            "text": f"{departed['username']} left the room",
            "time": formatted_time(),
        }
        room["chat"].append(sys_msg)
        if len(room["chat"]) > 100:
            room["chat"].pop(0)
        await sio.emit("new-chat-message", sys_msg, room=room_id)

        remaining_admins = [u for u in room["users"].values() if u.get("isAdmin")]
        if not remaining_admins:
            next_user = next(iter(room["users"].values()))
            next_user["isAdmin"] = True
            await sio.emit("role-updated", {"isAdmin": True}, to=next_user["socketId"])
            await sio.emit("user-list-updated", list(room["users"].values()), room=room_id)
