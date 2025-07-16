import os
import requests
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USER_NAME = "Anime(AMK4UP)"  # اسم العرض في الرسالة (غير مستخدم حالياً)
DISCORD_USER_ID = "1395041371181809754"  # رقم المستخدم (لعمل منشن)

def send_discord_notification(anime_title, episode_number, episode_link, image_url=None, reason=None):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL غير موجود في متغيرات البيئة.")
        return

    # نص السبب الافتراضي عند عدم تحديد reason
    reason_text = reason if reason else "🎉 تم إصدار حلقة جديدة!"

    embed = {
        "title": f"{anime_title} - الحلقة {episode_number}",
        "url": episode_link,
        "description": f"{reason_text}\n<@{DISCORD_USER_ID}>\nرابط المشاهدة:\n[اضغط هنا للمشاهدة]({episode_link})",
        "color": 0x1ABC9C,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}
        embed["image"] = {"url": image_url}

    payload = {
        "content": f"<@{DISCORD_USER_ID}>",
        "embeds": [embed],
        "allowed_mentions": {
            "users": [DISCORD_USER_ID]
        },
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("📢 تم إرسال إشعار إلى Discord.")
        else:
            print(f"❌ فشل إرسال الإشعار: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال الإشعار إلى Discord: {e}")


# --- أمثلة على الاستخدام ---

# 1. إرسال إشعار إصدار حلقة جديدة (الافتراضي)
send_discord_notification(
    anime_title="اسم الأنمي",
    episode_number="5",
    episode_link="https://example.com/episode/5",
    image_url="https://example.com/image.webp"
)

# 2. إرسال إشعار لتحديث حلقة بسبب إضافة سيرفر جديد مثلاً
send_discord_notification(
    anime_title="اسم الأنمي",
    episode_number="5",
    episode_link="https://example.com/episode/5",
    image_url="https://example.com/image.webp",
    reason="🔄 تم تحديث الحلقة بإضافة سيرفر جديد!"
)
