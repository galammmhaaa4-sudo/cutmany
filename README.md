# 🎬 نظام أتمتة قناة الكرتون على يوتيوب

> نظام Python مجاني بالكامل يعمل على GitHub Actions - يقطع فيديوهات الكرتون تلقائياً ويرفعها على يوتيوب!

---

## 📋 جدول المحتويات
1. [كيف يعمل النظام](#كيف-يعمل)
2. [متطلبات الإعداد](#متطلبات-الإعداد)
3. [خطوات الإعداد](#خطوات-الإعداد)
4. [إعداد GitHub Secrets](#إعداد-github-secrets)
5. [تخصيص الإعدادات](#تخصيص-الإعدادات)
6. [تشغيل النظام](#تشغيل-النظام)

---

## ⚙️ كيف يعمل

```
كل يوم تلقائياً:
Google Drive  →  تنزيل  →  تقطيع  →  Letterbox  →  Queue

كل ساعتين تلقائياً:
Queue  →  رفع مقطع واحد  →  يوتيوب
```

---

## 🛠️ متطلبات الإعداد

- حساب GitHub مجاني
- حساب Google Drive
- قناة يوتيوب
- Google Cloud Console (مجاني) لإنشاء API credentials

---

## 📝 خطوات الإعداد

### الخطوة 1: إعداد Google Drive Service Account

1. اذهب إلى Google Cloud Console: https://console.cloud.google.com/
2. أنشئ مشروعاً جديداً
3. فعّل **Google Drive API**
4. اذهب إلى **Credentials** → **Create Credentials** → **Service Account**
5. حمّل ملف JSON للـ Service Account
6. شارك مجلد Drive مع إيميل الـ Service Account

### الخطوة 2: الحصول على YouTube Refresh Token

هذه الخطوة تحتاجها **مرة واحدة فقط**:

```bash
# 1. ثبّت المكتبات
pip install google-auth-oauthlib

# 2. اذهب إلى Google Cloud Console
#    - فعّل YouTube Data API v3
#    - أنشئ OAuth 2.0 Client ID (نوع: Desktop application)
#    - حمّل ملف client_secrets.json

# 3. شغّل هذا الكود للحصول على الـ Token
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
# سيفتح المتصفح - سجّل دخولك بحساب يوتيوب
# انسخ الـ Refresh Token الظاهر في الـ Terminal
```

### الخطوة 3: ضع شعار قناتك

- استبدل ملف `assets/channel_banner.png` بشعار قناتك
- يُفضل أن يكون الشعار عرضياً (landscape) بخلفية شفافة (PNG)

### الخطوة 4: عدّل config.yml

```yaml
cartoon:
  name: "اسم كرتونك هنا"
  episode_number: 1
```

---

## 🔐 إعداد GitHub Secrets

اذهب إلى: Repository → Settings → Secrets and variables → Actions → New repository secret

| اسم السر | القيمة | من أين |
|----------|--------|--------|
| `GOOGLE_DRIVE_CREDENTIALS` | محتوى ملف JSON كاملاً | Google Cloud - Service Account |
| `GOOGLE_DRIVE_FOLDER_ID` | ID مجلد Drive | من رابط المجلد |
| `YOUTUBE_CLIENT_ID` | Client ID | Google Cloud - OAuth 2.0 |
| `YOUTUBE_CLIENT_SECRET` | Client Secret | Google Cloud - OAuth 2.0 |
| `YOUTUBE_REFRESH_TOKEN` | Refresh Token | من الخطوة 2 |

#### كيف تجد ID مجلد Google Drive؟
```
رابط المجلد: https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
الـ ID هو الجزء الأخير من الرابط بعد /folders/
```

---

## ⚙️ تخصيص الإعدادات

افتح `config.yml` وعدّل:

```yaml
cartoon:
  name: "Dragon Ball Z"
  episode_number: 15

youtube:
  upload_interval_hours: 2

letterbox:
  bar_height: 80
  bar_color: "#1a1a2e"
```

---

## 🚀 تشغيل النظام

### تشغيل يدوي (للاختبار):
1. اذهب إلى GitHub → Actions
2. اختر "🎬 Daily Cartoon Processing"
3. اضغط "Run workflow"

### تشغيل تلقائي:
- **المعالجة**: كل يوم الساعة 4 صباحاً (توقيت الرياض)
- **الرفع**: كل ساعتين تلقائياً

### إضافة حلقة جديدة:
1. ارفع الفيديو إلى مجلد Google Drive
2. غيّر `episode_number` في `config.yml`
3. النظام سيعالجه تلقائياً!

---

## 📁 هيكل المشروع

```
haceme/
├── .github/workflows/
│   ├── daily_trigger.yml      # معالجة يومية
│   └── upload_scheduler.yml   # رفع كل ساعتين
├── scripts/
│   ├── download_from_drive.py # تنزيل من Drive
│   ├── split_video.py         # تقطيع الفيديو
│   ├── add_letterbox.py       # إضافة شريط الـ Branding
│   ├── generate_metadata.py   # توليد عنوان ووصف
│   └── upload_to_youtube.py   # الرفع على يوتيوب
├── assets/
│   └── channel_banner.png     # شعار القناة (غيّره!)
├── queue/
│   └── upload_queue.json      # قائمة الانتظار (تلقائية)
├── config.yml                 # الإعدادات الرئيسية
└── requirements.txt           # مكتبات Python
```

---

## ⚠️ حدود الاستخدام المجاني

| الخدمة | الحد المجاني | ملاحظة |
|--------|-------------|--------|
| GitHub Actions | 2,000 دقيقة/شهر | كافي لـ ~10 حلقات/شهر |
| YouTube API | 10,000 وحدة/يوم | ≈ 6 فيديوهات/يوم |
| Google Drive API | 1 مليار طلب/يوم | أكثر من كافي |

---

مجاني 100% | يعمل 24/7 بدون تدخل يدوي
# cutmany
