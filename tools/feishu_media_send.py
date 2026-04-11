#!/usr/bin/env python3
"""
feishu_media_send.py — Send videos and images to 朱江 via Feishu REST API (Trinity v3 app).

Usage:
    python3 feishu_media_send.py <file_path> [--caption "描述文字"]
    python3 feishu_media_send.py <file1> <file2> ... [--caption "描述"]

Supported formats:
    Video: .mp4
    Image: .png, .jpg, .jpeg, .webp, .gif

Uses trinity-v3 app credentials from ~/.openclaw-trinity-v3/openclaw.json
Target: 朱江 (ou_f95c1768f6c33127ef2f248e45ccb658)
"""

import argparse
import fcntl
import json
import sys
from pathlib import Path

import requests

FEISHU_BASE = "https://open.feishu.cn/open-apis"
TOKEN_URL = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
FILE_UPLOAD_URL = f"{FEISHU_BASE}/im/v1/files"
IMAGE_UPLOAD_URL = f"{FEISHU_BASE}/im/v1/images"
MESSAGE_URL = f"{FEISHU_BASE}/im/v1/messages"

ZHU_JIANG_OPEN_ID = "ou_f95c1768f6c33127ef2f248e45ccb658"
CONFIG_PATH = Path.home() / ".openclaw-trinity-v3" / "openclaw.json"

UPLOAD_TIMEOUT = 180
SEND_TIMEOUT = 30

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4"}

DEFAULT_DEDUP_FILE = Path("/Users/ahzhu_agent/.openclaw-trinity-v3/workspace/sent-videos.txt")


def is_already_sent(dedup_path, abs_path):
    """Check if abs_path is already in dedup file (with shared lock)."""
    if not dedup_path.exists():
        return False
    with open(dedup_path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return abs_path in {line.strip() for line in f}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def record_sent(dedup_path, abs_path):
    """Append abs_path to dedup file (with exclusive lock)."""
    with open(dedup_path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(abs_path + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def detect_file_type(file_path):
    ext = Path(file_path).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return None


def get_token():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    feishu = config["channels"]["feishu"]
    resp = requests.post(TOKEN_URL, json={
        "app_id": feishu["appId"],
        "app_secret": feishu["appSecret"]
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def upload_video(token, file_path):
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        resp = requests.post(FILE_UPLOAD_URL, headers=headers,
            data={"file_type": "mp4", "file_name": Path(file_path).name},
            files={"file": (Path(file_path).name, f)},
            timeout=UPLOAD_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"上传失败: {data}")
    file_key = data["data"]["file_key"]
    print(f"  ✅ 上传成功: {Path(file_path).name} → {file_key}")
    return file_key


def upload_image(token, file_path):
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        resp = requests.post(IMAGE_UPLOAD_URL, headers=headers,
            files={
                "image_type": (None, "message"),
                "image": (Path(file_path).name, f, "application/octet-stream"),
            },
            timeout=UPLOAD_TIMEOUT)
    data = resp.json()
    if resp.status_code != 200 or data.get("code") != 0:
        raise Exception(f"上传图片失败 (HTTP {resp.status_code}): {data}")
    image_key = data["data"]["image_key"]
    print(f"  ✅ 上传成功: {Path(file_path).name} → {image_key}")
    return image_key


def send_text(token, text, chat_id=ZHU_JIANG_OPEN_ID):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    body = {"receive_id": chat_id, "msg_type": "text", "content": json.dumps({"text": text})}
    resp = requests.post(f"{MESSAGE_URL}?receive_id_type=open_id", headers=headers, json=body, timeout=SEND_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"发送文本失败: {data}")
    print(f"  ✅ 文本已发送: {text[:50]}...")


def send_video(token, file_key, chat_id=ZHU_JIANG_OPEN_ID):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    body = {"receive_id": chat_id, "msg_type": "media", "content": json.dumps({"file_key": file_key})}
    resp = requests.post(f"{MESSAGE_URL}?receive_id_type=open_id", headers=headers, json=body, timeout=SEND_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"发送视频失败: {data}")
    print(f"  ✅ 视频已发送")


def send_image(token, image_key, chat_id=ZHU_JIANG_OPEN_ID):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    body = {"receive_id": chat_id, "msg_type": "image", "content": json.dumps({"image_key": image_key})}
    resp = requests.post(f"{MESSAGE_URL}?receive_id_type=open_id", headers=headers, json=body, timeout=SEND_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"发送图片失败: {data}")
    print(f"  ✅ 图片已发送")


def send_file(token, file_path, chat_id):
    ftype = detect_file_type(file_path)
    print(f"\n📤 发送: {Path(file_path).name} ({ftype})")
    if ftype == "video":
        file_key = upload_video(token, file_path)
        send_video(token, file_key, chat_id)
    elif ftype == "image":
        image_key = upload_image(token, file_path)
        send_image(token, image_key, chat_id)


def main():
    parser = argparse.ArgumentParser(description="Send media (videos/images) to 朱江 via Feishu")
    parser.add_argument("files", nargs="+", help="Media file path(s): .mp4 (video), .png/.jpg/.jpeg/.webp/.gif (image)")
    parser.add_argument("--caption", default=None, help="Caption text sent before media files")
    parser.add_argument("--chat-id", default=ZHU_JIANG_OPEN_ID, help="Override target chat ID")
    parser.add_argument("--dedup-file", default=str(DEFAULT_DEDUP_FILE),
                        help=f"Path to dedup tracking file (default: {DEFAULT_DEDUP_FILE})")
    parser.add_argument("--force", action="store_true", help="Bypass dedup check and send anyway")
    parser.add_argument("--no-dedup", action="store_true", help="Disable dedup entirely (don't check or record)")
    args = parser.parse_args()

    use_dedup = not args.no_dedup and not args.force
    dedup_path = Path(args.dedup_file) if use_dedup else None

    # Validate paths and file types
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"❌ 文件不存在: {f}", file=sys.stderr)
            sys.exit(1)
        if detect_file_type(f) is None:
            print(f"❌ 不支持的文件类型: {p.suffix} ({f})", file=sys.stderr)
            print(f"   支持: {', '.join(sorted(VIDEO_EXTENSIONS | IMAGE_EXTENSIONS))}", file=sys.stderr)
            sys.exit(1)

    token = get_token()
    print(f"🔑 Token 获取成功")

    if args.caption:
        send_text(token, args.caption, args.chat_id)

    for f in args.files:
        abs_path = str(Path(f).resolve())
        if dedup_path and is_already_sent(dedup_path, abs_path):
            print(f"⏭️ 已发送过，跳过: {Path(f).name}")
            continue
        send_file(token, f, args.chat_id)
        if dedup_path:
            record_sent(dedup_path, abs_path)

    n_vid = sum(1 for f in args.files if detect_file_type(f) == "video")
    n_img = sum(1 for f in args.files if detect_file_type(f) == "image")
    parts = []
    if n_vid:
        parts.append(f"{n_vid} 个视频")
    if n_img:
        parts.append(f"{n_img} 张图片")
    print(f"\n🎉 完成 — 共发送 {'、'.join(parts)}")


if __name__ == "__main__":
    main()
