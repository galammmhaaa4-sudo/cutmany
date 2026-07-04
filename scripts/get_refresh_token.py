"""
get_refresh_token.py
====================
سكريبت مؤقت لتوليد Refresh Token لحساب يوتيوب.
يقوم بفتح متصفحك لتسجيل الدخول ويطبع الـ Token في النهاية.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    client_secrets_path = "client_secrets.json"
    
    if not os.path.exists(client_secrets_path):
        print(f"❌ لم يتم العثور على {client_secrets_path}")
        print("تأكد من تحميل ملف مفتاح OAuth وتسميته client_secrets.json في نفس المجلد.")
        return
        
    print("⏳ جاري بدء خادم التفويض المحلي...")
    print("سيتم فتح متصفحك الآن لتسجيل الدخول بحساب يوتيوب...")
    
    # استخدام InstalledAppFlow لطلب التوكن
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    
    print("\n" + "="*80)
    print("🎉 تم تسجيل الدخول بنجاح!")
    print("الـ Refresh Token الخاص بك هو:")
    print(creds.refresh_token)
    print("="*80)
    print("\n⚠️  قم بنسخ هذا التوكن بالكامل واحفظه لاستخدامه في GitHub Secrets كـ YOUTUBE_REFRESH_TOKEN")

if __name__ == "__main__":
    main()
