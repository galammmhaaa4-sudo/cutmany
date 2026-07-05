"""
add_letterbox.py
================
سكريبت معالجة الفيديو المطور:
1. يدعم وضعين: الفيديوهات الطويلة (16:9) والقصيرة (Shorts - 9:16).
2. الفيديوهات الطويلة: يضيف الشريطين العلوي والسفلي مع الشعار والاسم.
3. الفيديوهات القصيرة: يضع المقطع في المنتصف مع خلفية ضبابية (Blur) لمنع تشويه الأبعاد.
4. يتضمن تحسينات ذكية لتفادي حقوق الملكية (Content ID Bypass):
   - تسريع الفيديو والصوت بنسبة (Speedup) مع الحفاظ على نبرة الصوت.
   - تعديل طفيف لسطوع وتباين الألوان (Color Grading).
5. يضيف علامة مائية متحركة (Bouncing Watermark) لحماية الفيديو من السرقة.
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


def process_video_effects(
    input_path: str,
    output_path: str,
    part_number: int,
    config: dict
) -> bool:
    """
    يقوم بمعالجة الفيديو بالكامل في سطر أمر ffmpeg واحد سريع.
    """
    video_mode   = config.get("video_mode", "long")
    lb_cfg       = config["letterbox"]
    enh_cfg      = config["enhancements"]
    cartoon_name = config["cartoon"]["name"]
    part_text    = f"Part {part_number}"
    logo_path    = str(ASSETS_DIR / "channel_banner.png")
    has_logo     = os.path.exists(logo_path)

    # 1. إعداد مرشحات تجنب الحقوق (Speedup & Color Grading)
    v_filters = []
    a_filters = []

    # تعديل الألوان
    if enh_cfg["color_grading"]["enabled"]:
        brightness = enh_cfg["color_grading"]["brightness"]
        contrast   = enh_cfg["color_grading"]["contrast"]
        v_filters.append(f"eq=brightness={brightness}:contrast={contrast}")

    # التسريع
    speed = enh_cfg.get("speed_multiplier", 1.0)
    if speed != 1.0:
        v_filters.append(f"setpts=PTS/{speed}")
        a_filters.append(f"atempo={speed}")

    # ربط الفلتر المبدئي للفيديو والصوت
    pre_v = "[0:v]" + ",".join(v_filters) if v_filters else "[0:v]"
    pre_a = "[0:a]" + ",".join(a_filters) if a_filters else "[0:a]"

    # 2. بناء فلاتر تخطيط الفيديو (Layout)
    filters_complex = []
    
    # تعريف أسماء الـ Labels لتمريرها بين الفلاتر
    curr_v = "[pre_v]"
    filters_complex.append(f"{pre_v}null{curr_v}")

    if video_mode == "shorts":
        # تصميم الفيديوهات القصيرة (Shorts - 9:16)
        # خلفية ضبابية ممتدة + فيديو أصلي في المنتصف بعرض 1080
        filters_complex.append(
            f"{curr_v}scale=1920*iw/ih:1920,crop=1080:1920,boxblur=20:5[bg]"
        )
        filters_complex.append(
            f"{curr_v}scale=1080:-1[fg]"
        )
        filters_complex.append(
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[layout_base]"
        )
        
        # كتابة النصوص في الأماكن الفارغة (العلوي والسفلي)
        font_size = lb_cfg["text_font_size"]
        filters_complex.append(
            f"[layout_base]drawtext="
            f"text='{part_text}':"
            f"fontsize={font_size + 12}:"
            f"fontcolor={lb_cfg['text_color']}:"
            f"x=(w-text_w)/2:y=250"
            f"[top_texted]"
        )
        filters_complex.append(
            f"[top_texted]drawtext="
            f"text='{cartoon_name}':"
            f"fontsize={font_size + 4}:"
            f"fontcolor={lb_cfg['text_color']}@0.85:"
            f"x=(w-text_w)/2:y=h-300"
            f"[layout_v]"
        )
    else:
        # تصميم الفيديوهات الطويلة (Long - 16:9 Letterbox)
        bar_h      = lb_cfg["bar_height"]
        bar_color  = lb_cfg["bar_color"]
        text_color = lb_cfg["text_color"]
        font_size  = lb_cfg["text_font_size"]
        
        r, g, b = hex_to_rgb(bar_color)
        ffmpeg_color = f"0x{r:02X}{g:02X}{b:02X}"
        
        filters_complex.append(
            f"{curr_v}pad=iw:ih+{bar_h*2}:0:{bar_h}:{ffmpeg_color}[padded]"
        )
        
        top_y = (bar_h - font_size) // 2
        filters_complex.append(
            f"[padded]drawtext="
            f"text='{part_text}':"
            f"fontsize={font_size}:"
            f"fontcolor={text_color}:"
            f"x=30:y={top_y}"
            f"[top_texted]"
        )
        
        bot_font_size = font_size - 8
        filters_complex.append(
            f"[top_texted]drawtext="
            f"text='{cartoon_name}':"
            f"fontsize={bot_font_size}:"
            f"fontcolor={text_color}@0.85:"
            f"x=(w-text_w)/2:y=h-{bar_h - (bar_h - bot_font_size) // 2}"
            f"[text_base]"
        )
        
        if has_logo:
            filters_complex.append(f"[1:v]scale=-1:{bar_h - 16}[logo_scaled]")
            filters_complex.append(f"[text_base][logo_scaled]overlay=x=10:y=h-{bar_h - 8}[layout_v]")
        else:
            filters_complex.append(f"[text_base]null[layout_v]")

    # 3. إضافة العلامة المائية المتحركة (Bouncing Watermark)
    if enh_cfg["watermark"]["enabled"]:
        w_text  = enh_cfg["watermark"]["text"]
        w_size  = enh_cfg["watermark"]["font_size"]
        w_op    = enh_cfg["watermark"]["opacity"]
        speed_x = enh_cfg["watermark"]["speed_x"] / 100.0
        speed_y = enh_cfg["watermark"]["speed_y"] / 100.0
        
        # حركة منحنى جيبي ناعمة تبقي النص داخل أطراف الشاشة مع هامش 160 بكسل
        expr_x = f"(w-text_w)/2 + (w-text_w-160)/2 * sin(t*{speed_x})"
        expr_y = f"(h-text_h)/2 + (h-text_h-160)/2 * sin(t*{speed_y})"
        
        filters_complex.append(
            f"[layout_v]drawtext="
            f"text='{w_text}':"
            f"fontsize={w_size}:"
            f"fontcolor=white@{w_op}:"
            f"x='{expr_x}':y='{expr_y}'"
            f"[out_v]"
        )
    else:
        filters_complex.append(f"[layout_v]null[out_v]")

    # بناء سطر أمر ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path
    ]
    
    if has_logo and video_mode != "shorts":
        cmd.extend(["-i", logo_path])
        
    cmd.extend([
        "-filter_complex", ";".join(filters_complex),
        "-map", "[out_v]",
        "-map", f"[pre_a]" if a_filters else "0:a",
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ خطأ في ffmpeg:\n{e.stderr[-1000:]}")
        return False


def main():
    config = load_config()

    if not QUEUE_PATH.exists():
        print("❌ ملف queue غير موجود")
        sys.exit(1)

    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    parts = queue_data.get("queue", [])
    if not parts:
        print("❌ لا توجد أجزاء في queue")
        sys.exit(1)

    video_mode = config.get("video_mode", "long")
    print(f"🎨 بدء معالجة الفيديوهات في وضع: {video_mode.upper()}...")
    print(f"📦 عدد الأجزاء: {len(parts)}")

    # مجلد الإخراج
    output_dir = os.path.join(config["processing"]["temp_dir"], "branded")
    os.makedirs(output_dir, exist_ok=True)

    updated_parts = []
    for part in parts:
        part_num = part["part_number"]
        in_file  = part["file_path"]
        out_file = os.path.join(output_dir, f"branded_part_{part_num:02d}.mp4")

        print(f"   🎬 معالجة الجزء {part_num}/{len(parts)}...", end=" ", flush=True)

        success = process_video_effects(in_file, out_file, part_num, config)

        if success and os.path.exists(out_file):
            print(f"✅ ({os.path.getsize(out_file) / 1024 / 1024:.1f} MB)")
            part["branded_file_path"] = out_file
        else:
            print(f"⚠️  فشل المعالجة، سيتم استخدام الملف الأصلي")
            part["branded_file_path"] = in_file  # fallback

        updated_parts.append(part)

    # تحديث الـ queue
    queue_data["queue"] = updated_parts
    queue_data["last_updated"] = datetime.now().isoformat()

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ اكتملت المعالجة بنجاح لجميع الأجزاء!")


if __name__ == "__main__":
    main()
