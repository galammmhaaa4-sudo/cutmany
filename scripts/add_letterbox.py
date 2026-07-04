"""
add_letterbox.py
================
يضيف شريطاً علوياً وسفلياً (Letterbox) لكل مقطع فيديو
يكتب "Part N" على الشريط العلوي
يضع شعار القناة على الشريط السفلي

يستخدم ffmpeg مع filter_complex
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime

# ── مسارات ───────────────────────────────────────────────────────────────────
CONFIG_PATH  = Path(__file__).parent.parent / "config.yml"
QUEUE_PATH   = Path(__file__).parent.parent / "queue" / "upload_queue.json"
ASSETS_DIR   = Path(__file__).parent.parent / "assets"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hex_to_rgb(hex_color: str) -> tuple:
    """يحوّل لون HEX إلى RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def add_letterbox_to_video(
    input_path: str,
    output_path: str,
    part_number: int,
    config: dict
) -> bool:
    """
    يضيف Letterbox لفيديو واحد باستخدام ffmpeg.
    
    التصميم:
    ┌─────────────────────────────────┐  ← شريط علوي بلون القناة
    │  Part N                         │
    ├─────────────────────────────────┤
    │       محتوى الفيديو الأصلي      │
    ├─────────────────────────────────┤
    │           اسم القناة            │  ← شريط سفلي
    └─────────────────────────────────┘
    """
    lb_cfg       = config["letterbox"]
    bar_h        = lb_cfg["bar_height"]        # 80px
    bar_color    = lb_cfg["bar_color"]          # #1a1a2e
    text_color   = lb_cfg["text_color"]         # #ffffff
    font_size    = lb_cfg["text_font_size"]     # 36
    logo_path    = str(ASSETS_DIR / "channel_banner.png")
    cartoon_name = config["cartoon"]["name"]

    # حساب لون الشريط بصيغة ffmpeg
    r, g, b = hex_to_rgb(bar_color)
    ffmpeg_color = f"0x{r:02X}{g:02X}{b:02X}"

    part_text    = f"Part {part_number}"
    has_logo     = os.path.exists(logo_path)

    # حساب y للنص العلوي والسفلي
    top_y    = (bar_h - font_size) // 2
    bot_y    = bar_h + "ih".replace("ih", "") # placeholder, computed below as expression

    # بناء filter_complex
    # خطوة 1: pad لإضافة شريطين
    pad_filter = (
        f"[0:v]pad=iw:ih+{bar_h*2}:0:{bar_h}:{ffmpeg_color}[padded]"
    )

    # خطوة 2: نص Part N على الشريط العلوي
    top_text_filter = (
        f"[padded]drawtext="
        f"text='{part_text}':"
        f"fontsize={font_size}:"
        f"fontcolor={text_color}:"
        f"x=30:"
        f"y={top_y}"
        f"[top_labeled]"
    )

    # خطوة 3: نص اسم القناة على الشريط السفلي
    bot_font_size = font_size - 8
    bot_text_filter = (
        f"[top_labeled]drawtext="
        f"text='{cartoon_name}':"
        f"fontsize={bot_font_size}:"
        f"fontcolor={text_color}@0.85:"
        f"x=(w-text_w)/2:"
        f"y=h-{bar_h - (bar_h - bot_font_size) // 2}"
        f"[final]"
    )

    if has_logo:
        # خطوة 4: إضافة الشعار
        logo_filter = f"[1:v]scale=-1:{bar_h - 16}[logo_scaled]"
        overlay_filter = f"[final][logo_scaled]overlay=x=10:y=h-{bar_h - 8}[out]"

        filter_complex = ";".join([
            pad_filter,
            top_text_filter,
            bot_text_filter,
            logo_filter,
            overlay_filter
        ])

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-i", logo_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        filter_complex = ";".join([
            pad_filter,
            top_text_filter,
            bot_text_filter.replace("[final]", "[out]")
        ])

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ خطأ في ffmpeg:\n{e.stderr[-800:]}")
        return False


def main():
    config = load_config()
    lb_cfg = config["letterbox"]

    if not QUEUE_PATH.exists():
        print("❌ ملف queue غير موجود")
        sys.exit(1)

    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    parts = queue_data.get("queue", [])
    if not parts:
        print("❌ لا توجد أجزاء في queue")
        sys.exit(1)

    print(f"🎨 بدء إضافة Letterbox لـ {len(parts)} جزء...")

    # مجلد الإخراج
    output_dir = os.path.join(config["processing"]["temp_dir"], "branded")
    os.makedirs(output_dir, exist_ok=True)

    logo_path = str(ASSETS_DIR / "channel_banner.png")
    if not os.path.exists(logo_path):
        print(f"⚠️  شعار القناة غير موجود في: {lb_cfg['logo_path']}")
        print(f"   سيتم الاستمرار بدون شعار (نص فقط)")

    updated_parts = []
    for part in parts:
        part_num = part["part_number"]
        in_file  = part["file_path"]
        out_file = os.path.join(output_dir, f"branded_part_{part_num:02d}.mp4")

        print(f"   🖼️  Part {part_num}...", end=" ", flush=True)

        success = add_letterbox_to_video(in_file, out_file, part_num, config)

        if success and os.path.exists(out_file):
            print(f"✅ ({os.path.getsize(out_file) / 1024 / 1024:.1f} MB)")
            part["branded_file_path"] = out_file
        else:
            print(f"⚠️  فشل، سيستخدم الملف الأصلي")
            part["branded_file_path"] = in_file  # fallback

        updated_parts.append(part)

    # تحديث الـ queue
    queue_data["queue"] = updated_parts
    queue_data["last_updated"] = datetime.now().isoformat()

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ تم إضافة Letterbox لجميع الأجزاء!")


if __name__ == "__main__":
    main()
