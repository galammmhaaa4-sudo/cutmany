"""
split_video.py
==============
يقطع الفيديو الطويل إلى مقاطع بين 4-5 دقائق
يستخدم ffmpeg مباشرة لأداء أسرع وجودة أعلى

المتطلبات:
- ffmpeg مثبت (يتم تثبيته تلقائياً في GitHub Actions)
- مسار الفيديو من download_from_drive.py
"""

import os
import sys
import json
import yaml
import subprocess
import math
from pathlib import Path
from datetime import datetime

# ── مسارات ───────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config.yml"
QUEUE_PATH  = Path(__file__).parent.parent / "queue" / "upload_queue.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_video_duration(video_path: str) -> float:
    """يحصل على مدة الفيديو بالثواني باستخدام ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def split_video(video_path: str, output_dir: str, config: dict) -> list[dict]:
    """
    يقطع الفيديو إلى مقاطع بحجم ثابت باستخدام ffmpeg.
    يختار مدة المقطع تلقائياً بين min_duration و max_duration
    بحيث يكون آخر مقطع ليس قصيراً جداً.
    
    يعيد قائمة بمعلومات كل مقطع.
    """
    min_dur = config["splitting"]["min_duration"]
    max_dur = config["splitting"]["max_duration"]
    
    total_duration = get_video_duration(video_path)
    print(f"⏱️  مدة الفيديو الأصلي: {total_duration/60:.1f} دقيقة")
    
    # اختيار أفضل مدة للتقطيع
    segment_duration = choose_best_segment_duration(total_duration, min_dur, max_dur)
    num_parts = math.ceil(total_duration / segment_duration)
    
    print(f"✂️  سيتم تقطيعه إلى {num_parts} أجزاء (كل جزء {segment_duration/60:.1f} دقيقة)")
    
    os.makedirs(output_dir, exist_ok=True)
    parts = []
    
    for i in range(num_parts):
        start_time = i * segment_duration
        part_num   = i + 1
        out_file   = os.path.join(output_dir, f"part_{part_num:02d}.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(segment_duration),
            "-c:v", "libx264",
            "-crf", "23",           # جودة عالية
            "-preset", "fast",      # سرعة معالجة معقولة
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_file
        ]
        
        print(f"   🔧 جزء {part_num}/{num_parts}...", end=" ")
        subprocess.run(cmd, capture_output=True, check=True)
        
        # التحقق من أن الملف موجود وحجمه معقول
        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
            print(f"✅ ({os.path.getsize(out_file) / 1024 / 1024:.1f} MB)")
            parts.append({
                "part_number": part_num,
                "file_path": out_file,
                "start_time": start_time,
                "duration": segment_duration,
                "uploaded": False,
                "youtube_id": None
            })
        else:
            print(f"⚠️  تحذير: الجزء {part_num} فارغ أو صغير جداً!")
    
    return parts


def choose_best_segment_duration(total: float, min_dur: int, max_dur: int) -> int:
    """
    يختار أفضل مدة للمقطع بحيث:
    - لا يكون أقصر من min_dur
    - لا يكون أطول من max_dur
    - يجعل الأجزاء متساوية قدر الإمكان
    """
    best_dur = max_dur
    best_remainder = float('inf')
    
    for dur in range(min_dur, max_dur + 1, 30):  # نجرب كل 30 ثانية
        num_parts = math.ceil(total / dur)
        remainder = (dur * num_parts) - total
        if remainder < best_remainder:
            best_remainder = remainder
            best_dur = dur
    
    return best_dur


def update_queue(parts: list, config: dict):
    """يحدّث ملف الـ queue بقائمة المقاطع الجاهزة."""
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
    
    queue_data["queue"] = parts
    queue_data["last_updated"] = datetime.now().isoformat()
    queue_data["total_parts"] = len(parts)
    queue_data["current_episode"]["total_parts"] = len(parts)
    
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)
    
    print(f"📋 تم تحديث queue بـ {len(parts)} أجزاء")


def main():
    config = load_config()
    
    # قراءة مسار الفيديو من الـ queue
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
    
    episode_info = queue_data.get("current_episode")
    if not episode_info or not episode_info.get("path"):
        print("❌ لا يوجد فيديو للمعالجة في queue")
        sys.exit(1)
    
    video_path = episode_info["path"]
    
    if not os.path.exists(video_path):
        print(f"❌ الفيديو غير موجود: {video_path}")
        sys.exit(1)
    
    # مجلد الإخراج
    output_dir = os.path.join(config["processing"]["temp_dir"], "parts")
    
    print(f"🎬 بدء تقطيع: {os.path.basename(video_path)}")
    parts = split_video(video_path, output_dir, config)
    
    if not parts:
        print("❌ فشل التقطيع - لم يتم إنشاء أي أجزاء")
        sys.exit(1)
    
    update_queue(parts, config)
    
    print(f"\n✅ تم التقطيع بنجاح! {len(parts)} أجزاء جاهزة للمرحلة التالية")


if __name__ == "__main__":
    main()
