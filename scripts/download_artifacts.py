"""
download_artifacts.py
=====================
سكريبت بايثون لتحميل أحدث ملفات الفيديو المعالجة (Artifacts) من تشغيلات Actions السابقة.
يتجاوز قيود Actions/download-artifact التي لا تدعم التحميل عبر تشغيلات مختلفة بشكل افتراضي.
"""

import os
import sys
import requests
import zipfile
import io

def download_latest_artifact():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")  # الصيغة: "owner/repo"
    
    if not token or not repo:
        print("❌ GITHUB_TOKEN أو GITHUB_REPOSITORY غير موجود في المتغيرات البيئية")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # 1. جلب قائمة الـ Artifacts من GitHub API
    url = f"https://api.github.com/repos/{repo}/actions/artifacts"
    print(f"🔍 جاري البحث عن ملفات معالجة في المستودع: {repo}...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ فشل جلب الـ Artifacts: {response.text}")
        sys.exit(1)
        
    artifacts = response.json().get("artifacts", [])
    
    # فلترة الملفات التي تبدأ بـ processed-videos-
    processed_artifacts = [a for a in artifacts if a["name"].startswith("processed-videos-")]
    
    if not processed_artifacts:
        print("⚠️ لم يتم العثور على أي ملفات معالجة (processed-videos) مرفوعة سابقاً.")
        sys.exit(0)
        
    # ترتيبها تنازلياً حسب تاريخ الإنشاء للحصول على الأحدث
    processed_artifacts.sort(key=lambda x: x["created_at"], reverse=True)
    latest_artifact = processed_artifacts[0]
    
    print(f"📦 وُجد أحدث ملف معالجة: {latest_artifact['name']} (ID: {latest_artifact['id']})")
    
    # 2. تحميل ملف الـ Zip
    download_url = latest_artifact["archive_download_url"]
    print(f"📥 جاري التحميل...")
    
    zip_response = requests.get(download_url, headers=headers)
    if zip_response.status_code != 200:
        print(f"❌ فشل تحميل الملف: {zip_response.text}")
        sys.exit(1)
        
    # 3. فك الضغط في المجلد المؤقت لرفعها على يوتيوب
    target_dir = "/tmp/cartoon_processing/branded"
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"📂 جاري فك الضغط إلى: {target_dir}...")
    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zip_ref:
        zip_ref.extractall(target_dir)
        
    print(f"✅ تم تحميل وفك ضغط جميع الملفات بنجاح!")
    print(f"📁 الملفات المتوفرة: {os.listdir(target_dir)}")

if __name__ == "__main__":
    download_latest_artifact()
