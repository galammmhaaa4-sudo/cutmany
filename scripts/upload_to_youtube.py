"""
upload_to_youtube.py
====================
يرفع أول مقطع غير محمّل من قائمة الانتظار إلى يوتيوب
يستخدم YouTube Data API v3 مع OAuth 2.0 Refresh Token

المتطلبات (GitHub Secrets):
- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN
"""

import os
import sys
import json
import yaml
import time
from pathlib import Path
from datetime import datetime

import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# ── مسارات ───────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config.yml"
QUEUE_PATH  = Path(__file__).parent.parent / "queue" / "upload_queue.json"
SCOPES      = ["https://www.googleapis.com/auth/youtube.upload"]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_youtube_service():
    """
    يبني YouTube service باستخدام Refresh Token المحفوظ في GitHub Secrets.
    الـ Refresh Token لا ينتهي مفعوله ما لم يتم إلغاؤه يدوياً.
    """
    client_id     = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        missing = [k for k, v in {
            "YOUTUBE_CLIENT_ID": client_id,
            "YOUTUBE_CLIENT_SECRET": client_secret,
            "YOUTUBE_REFRESH_TOKEN": refresh_token
        }.items() if not v]
        raise EnvironmentError(f"❌ المتغيرات التالية مفقودة: {', '.join(missing)}")
    
    credentials = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES
    )
    
    # تجديد الـ Token تلقائياً
    credentials.refresh(Request())
    
    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, part: dict) -> str:
    """
    يرفع فيديو واحد إلى يوتيوب مع metadata كاملة.
    يعيد ID الفيديو على يوتيوب.
    """
    video_path = part.get("branded_file_path") or part.get("file_path")
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"❌ الملف غير موجود: {video_path}")
    
    file_size = os.path.getsize(video_path)
    print(f"📤 جاري رفع: {os.path.basename(video_path)}")
    print(f"   الحجم: {file_size / 1024 / 1024:.1f} MB")
    
    # بيانات الفيديو
    body = {
        "snippet": {
            "title":       part["youtube_title"],
            "description": part["youtube_description"],
            "tags":        part.get("youtube_tags", []),
            "categoryId":  part.get("youtube_category", "1")
        },
        "status": {
            "privacyStatus":           part.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": False
        }
    }
    
    # رفع الفيديو بشكل تدريجي (resumable upload)
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024  # 10MB per chunk
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    # رفع مع تتبع التقدم
    response = None
    retry_count = 0
    max_retries = 5
    
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"   ↳ رُفع {progress}%", end="\r")
        except Exception as e:
            retry_count += 1
            if retry_count > max_retries:
                raise
            wait_time = 2 ** retry_count  # Exponential backoff
            print(f"\n   ⚠️  خطأ مؤقت، إعادة المحاولة بعد {wait_time} ثانية...")
            time.sleep(wait_time)
    
    video_id = response.get("id")
    print(f"\n✅ تم الرفع! رابط الفيديو: https://youtu.be/{video_id}")
    return video_id


def main():
    config = load_config()
    
    # قراءة الـ queue
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
    
    parts = queue_data.get("queue", [])
    
    # البحث عن أول جزء لم يتم رفعه
    pending = [p for p in parts if not p.get("uploaded")]
    
    if not pending:
        print("✅ جميع الأجزاء تم رفعها مسبقاً!")
        sys.exit(0)
    
    next_part = pending[0]
    part_num  = next_part["part_number"]
    
    print(f"🎬 جاري رفع الجزء {part_num} من {len(parts)}...")
    
    # الاتصال بيوتيوب
    print("🔗 جاري الاتصال بـ YouTube...")
    youtube = get_youtube_service()
    
    # الرفع
    try:
        video_id = upload_video(youtube, next_part)
        
        # تحديث حالة الجزء في الـ queue
        for part in parts:
            if part["part_number"] == part_num:
                part["uploaded"]   = True
                part["youtube_id"] = video_id
                part["upload_time"] = datetime.now().isoformat()
                break
        
        queue_data["queue"]        = parts
        queue_data["total_uploaded"] = sum(1 for p in parts if p.get("uploaded"))
        queue_data["last_updated"] = datetime.now().isoformat()
        
        with open(QUEUE_PATH, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)
        
        # كتابة نتيجة للـ GitHub Actions
        remaining = sum(1 for p in parts if not p.get("uploaded"))
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
            f.write(f"uploaded_video_id={video_id}\n")
            f.write(f"remaining_parts={remaining}\n")
        
        print(f"\n🎉 تم رفع الجزء {part_num} بنجاح!")
        print(f"   متبقي: {remaining} أجزاء")
        
    except Exception as e:
        print(f"❌ فشل الرفع: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
