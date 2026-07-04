"""
add_letterbox.py
================
يضيف شريطاً علوياً وسفلياً (Letterbox) لكل مقطع فيديو
يكتب "Part N" على الشريط العلوي
يضع شعار القناة على الشريط السفلي

يستخدم ffmpeg مع filter_complex لأداء عالي
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
FONT_PATH    = str(ASSETS_DIR / "font.ttf")   # خط مضمّن في المشروع


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
    يضيف Letterbox لفيديو واحد باستخدام ffmpeg filter_complex.
    
    التصميم:
    ┌─────────────────────────────────┐  ← شريط علوي: نص "Part N" + تدرج لوني
    │  Part N          [Channel Logo] │
    ├─────────────────────────────────┤
    │                                 │
    │       محتوى الفيديو الأصلي      │
    │                                 │
    ├─────────────────────────────────┤
    │  [Logo]    اسم القناة           │  ← شريط سفلي: شعار + اسم القناة
    └─────────────────────────────────┘
    """
    lb_cfg      = config["letterbox"]
    bar_h       = lb_cfg["bar_height"]      # 80px
    bar_color   = lb_cfg["bar_color"]       # #1a1a2e
    text_color  = lb_cfg["text_color"]      # #ffffff
    font_size   = lb_cfg["text_font_size"]  # 36
    logo_path   = str(Path(__file__).parent.parent / lb_cfg["logo_path"])
    cartoon_name = config["cartoon"]["name"]
    
    # حساب لون الشريط بصيغة ffmpeg (0xRRGGBB)
    r, g, b = hex_to_rgb(bar_color)
    ffmpeg_color = f"0x{r:02X}{g:02X}{b:02X}"
    
    # نص الجزء
    part_text = f"Part {part_number}"
    
    # التحقق من وجود الخط
    font_opt = f"fontfile='{FONT_PATH}':" if os.path.exists(FONT_PATH) else ""
    
    if has_logo:
        # Filter مع شعار
        filter_complex = (
            # 1. إضافة padding علوي وسفلي
            f"[0:v]pad=width=iw:height=ih+{bar_h*2}:"
            f"x=0:y={bar_h}:color={ffmpeg_color}[padded];"
            
            # 2. كتابة نص "Part N" على الشريط العلوي (يسار)
            f"[padded]drawtext="
            f"text='{part_text}':"
            f"fontsize={font_size}:"
            f"fontcolor={text_color}:"
            f"x=30:y={bar_h//2 - font_size//2}:"
            f"{font_opt}"
            f"box=0[texted];"
            
            # 3. كتابة اسم القناة على الشريط السفلي
            f"[texted]drawtext="
            f"text='{cartoon_name}':"
            f"fontsize={font_size - 8}:"
            f"fontcolor={text_color}@0.8:"
            f"x=(w-text_w)/2:y=h-{bar_h//2 + font_size//2 - 8}:"
            f"{font_opt.replace(':', '')}[final];" # remove trailing colon for last argument if present
            
            # 4. وضع الشعار على الشريط السفلي (يسار)
            f"[1:v]scale=-1:{bar_h - 20}[logo];"
            f"[final][logo]overlay=x=10:y=main_h-{bar_h - 10}[out]"
        )
        
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
        # Filter بدون شعار (نص فقط)
        filter_complex = (
            f"[0:v]pad=width=iw:height=ih+{bar_h*2}:"
            f"x=0:y={bar_h}:color={ffmpeg_color}[padded];"
            
            f"[padded]drawtext="
            f"text='{part_text}':"
            f"fontsize={font_size}:"
            f"fontcolor={text_color}:"
            f"x=30:y={bar_h//2 - font_size//2}:"
            f"{font_opt}"
            f"box=0[texted];"
            
            f"[texted]drawtext="
            f"text='{cartoon_name}':"
            f"fontsize={font_size - 8}:"
            f"fontcolor={text_color}@0.8:"
            f"x=(w-text_w)/2:y=h-{bar_h//2 + font_size//2 - 8}:"
            f"{font_opt.replace(':', '')}[out]"
        )
        
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ خطأ في ffmpeg: {e.stderr[-500:]}")
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
    
    # مجلد الإخراج للأجزاء المحسّنة
    output_dir = os.path.join(config["processing"]["temp_dir"], "branded")
    os.makedirs(output_dir, exist_ok=True)
    
    updated_parts = []
    logo_exists = os.path.exists(
        str(Path(__file__).parent.parent / lb_cfg["logo_path"])
    )
    
    if not logo_exists:
        print(f"⚠️  شعار القناة غير موجود في: {lb_cfg['logo_path']}")
        print(f"   سيتم الاستمرار بدون شعار (نص فقط)")
    
    for part in parts:
        part_num  = part["part_number"]
        in_file   = part["file_path"]
        out_file  = os.path.join(output_dir, f"branded_part_{part_num:02d}.mp4")
        
        print(f"   🖼️  Part {part_num}...", end=" ")
        
        success = add_letterbox_to_video(in_file, out_file, part_num, config)
        
        if success and os.path.exists(out_file):
            print(f"✅")
            part["branded_file_path"] = out_file
        else:
            print(f"⚠️  فشل، سيستخدم الملف الأصلي")
            part["branded_file_path"] = in_file  # fallback للأصل
        
        updated_parts.append(part)
    
    # تحديث الـ queue
    queue_data["queue"] = updated_parts
    queue_data["last_updated"] = datetime.now().isoformat()
    
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم إضافة Letterbox لجميع الأجزاء!")


if __name__ == "__main__":
    main()
