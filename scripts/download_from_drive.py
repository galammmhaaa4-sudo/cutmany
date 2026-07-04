"""
download_from_drive.py
======================
يقوم بتنزيل أول فيديو غير معالج من مجلد Google Drive المحدد في config.yml
يستخدم Google Drive API v3 عبر Service Account

المتطلبات:
- GOOGLE_DRIVE_CREDENTIALS: محتوى ملف JSON للـ Service Account (GitHub Secret)
- GOOGLE_DRIVE_FOLDER_ID: ID المجلد في Drive (GitHub Secret)
"""

import os
import json
import yaml
import sys
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# ── إعدادات ──────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config.yml"
QUEUE_PATH  = Path(__file__).parent.parent / "queue" / "upload_queue.json"
SCOPES      = ["https://www.googleapis.com/auth/drive.readonly"]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_drive_service():
    """يبني Google Drive service من الـ Secret المحفوظ في بيئة GitHub Actions."""
    creds_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
    if not creds_json:
        raise EnvironmentError("❌ GOOGLE_DRIVE_CREDENTIALS غير موجود في المتغيرات البيئية")
    
    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def find_unprocessed_video(service, folder_id: str) -> dict | None:
    """
    يبحث عن أول فيديو في مجلد Drive غير مُعالج بعد.
    يُعتبر الفيديو غير مُعالج إذا لم يكن اسمه يبدأ بـ [DONE].
    """
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType contains 'video/' "
        f"and name != '[DONE]' "
        f"and trashed = false"
    )
    results = service.files().list(
        q=query,
        fields="files(id, name, size)",
        orderBy="createdTime",
        pageSize=1
    ).execute()
    
    files = results.get("files", [])
    return files[0] if files else None


def download_video(service, file_id: str, file_name: str, dest_dir: str) -> str:
    """ينزّل الفيديو من Drive إلى المسار المحدد ويعرض شريط التقدم."""
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file_name)
    
    request = service.files().get_media(fileId=file_id)
    
    print(f"📥 جاري تنزيل: {file_name}")
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"   ↳ {progress}%", end="\r")
    
    print(f"\n✅ تم التنزيل: {dest_path}")
    return dest_path


def save_video_info_to_queue(video_name: str, video_path: str, config: dict):
    """يحفظ معلومات الفيديو في ملف الـ queue لاستخدامها لاحقاً."""
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
    
    queue_data["current_episode"] = {
        "name": video_name,
        "path": video_path,
        "episode_number": config["cartoon"]["episode_number"],
        "cartoon_name": config["cartoon"]["name"]
    }
    
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)
    
    print(f"📋 تم حفظ معلومات الفيديو في queue")


def main():
    config = load_config()
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        raise EnvironmentError("❌ GOOGLE_DRIVE_FOLDER_ID غير موجود في المتغيرات البيئية")
    
    temp_dir = config["processing"]["temp_dir"]
    
    print("🔗 جاري الاتصال بـ Google Drive...")
    service = get_drive_service()
    
    print("🔍 جاري البحث عن فيديو غير معالج...")
    video = find_unprocessed_video(service, folder_id)
    
    if not video:
        print("⚠️  لا يوجد فيديو جديد للمعالجة. انتهى البرنامج.")
        # كتابة متغير بيئي لإيقاف workflow إذا لا يوجد شيء
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
            f.write("has_video=false\n")
        sys.exit(0)
    
    print(f"🎬 وُجد فيديو: {video['name']}")
    
    # تنزيل الفيديو
    video_path = download_video(service, video["id"], video["name"], temp_dir)
    
    # حفظ المعلومات
    save_video_info_to_queue(video["name"], video_path, config)
    
    # كتابة المسار كـ output للـ GitHub Actions
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write(f"video_path={video_path}\n")
        f.write(f"video_name={video['name']}\n")
        f.write("has_video=true\n")
    
    print("✅ جاهز للمرحلة التالية: التقطيع")


if __name__ == "__main__":
    main()
