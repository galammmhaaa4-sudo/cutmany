"""
generate_metadata.py
====================
يولّد عنوان ووصف تلقائي لكل مقطع فيديو
بناءً على القوالب المحددة في config.yml
"""

import json
import yaml
from pathlib import Path
from datetime import datetime


CONFIG_PATH = Path(__file__).parent.parent / "config.yml"
QUEUE_PATH  = Path(__file__).parent.parent / "queue" / "upload_queue.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sanitize_tag(text: str) -> str:
    """يحول اسم الكرتون إلى هاشتاق صالح."""
    return text.replace(" ", "_").replace("-", "_").lower()


def generate_title(config: dict, part_number: int) -> str:
    """يولّد عنوان الفيديو."""
    template = config["metadata_templates"]["title"]
    return template.format(
        cartoon_name=config["cartoon"]["name"],
        episode=config["cartoon"]["episode_number"],
        part=part_number
    )


def generate_description(config: dict, part_number: int, total_parts: int) -> str:
    """يولّد وصف الفيديو مع معلومات الأجزاء الأخرى."""
    template = config["metadata_templates"]["description"]
    
    description = template.format(
        cartoon_name=config["cartoon"]["name"],
        episode=config["cartoon"]["episode_number"],
        part=part_number,
        cartoon_name_tag=sanitize_tag(config["cartoon"]["name"])
    )
    
    # إضافة روابط الأجزاء الأخرى (placeholder)
    if total_parts > 1:
        description += f"\n\n📋 الحلقة مقسمة إلى {total_parts} أجزاء - تابع الأجزاء الأخرى على القناة!"
    
    return description


def generate_tags(config: dict) -> list:
    """يولّد قائمة الوسوم."""
    base_tags = config["youtube"]["tags"].copy()
    cartoon_tag = sanitize_tag(config["cartoon"]["name"])
    ep_tag = f"episode{config['cartoon']['episode_number']}"
    
    return base_tags + [cartoon_tag, ep_tag]


def main():
    config = load_config()
    
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)
    
    parts = queue_data.get("queue", [])
    total_parts = len(parts)
    
    print(f"📝 توليد Metadata لـ {total_parts} جزء...")
    
    updated_parts = []
    for part in parts:
        part_num = part["part_number"]
        
        part["youtube_title"]       = generate_title(config, part_num)
        part["youtube_description"] = generate_description(config, part_num, total_parts)
        part["youtube_tags"]        = generate_tags(config)
        part["youtube_category"]    = config["youtube"]["category_id"]
        part["privacy_status"]      = config["youtube"]["privacy_status"]
        
        print(f"   ✅ Part {part_num}: {part['youtube_title']}")
        updated_parts.append(part)
    
    queue_data["queue"] = updated_parts
    queue_data["last_updated"] = datetime.now().isoformat()
    
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم توليد جميع البيانات الوصفية!")


if __name__ == "__main__":
    main()
