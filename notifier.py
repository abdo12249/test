# notifier.py
import os
import requests
import json
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USER_NAME = "Anime(AMK4UP)"  # الاسم العام
YOUR_USER_ID = "1395041371181809754"  # معرفك في Discord
FAVORITES_FILE = "favorites.json"

def load_favorites():
    if not os.path.exists(FAVORITES_FILE):
        return {}
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ ملف المفضلات غير صالح، سيتم تجاهله.")
        return {}

def send_discord_notification(anime_title, episode_number, episode_link, image_url=None):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL غير موجود في متغيرات البيئة.")
        return

    favorites = load_favorites()
    sent_to_any = False

    # إرسال حسب المفضلات
    for user_id, anime_list in favorites.items():
        if anime_title not in anime_list:
            continue

        embed = {
            "title": f"{anime_title} - الحلقة {episode_number}",
            "url": episode_link,
            "description": f"🎉 تم إصدار حلقة جديدة!\n<@{user_id}>",
            "color": 0x1ABC9C,
            "timestamp": datetime.utcnow().isoformat()
        }

        if image_url:
            embed["thumbnail"] = {"url": image_url}
            embed["image"] = {"url": image_url}

        payload = {
            "content": f"<@{user_id}>",
            "embeds": [embed],
            "allowed_mentions": {
                "users": [user_id]
            },
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 5,
                            "label": "🎬 مشاهدة الآن",
                            "url": episode_link
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
            if response.status_code in [200, 204]:
                print(f"📢 أُرسل الإشعار إلى <@{user_id}>.")
                sent_to_any = True
            else:
                print(f"❌ فشل إرسال الإشعار لـ {user_id}: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ خطأ أثناء إرسال الإشعار لـ {user_id}: {e}")

    # إذا لم يُرسل لأي أحد في المفضلات، أرسل لك أنت بصيغة الاسم فقط
    if not sent_to_any:
        # تحقق هل لديك مفضلات؟
        your_animes = favorites.get(YOUR_USER_ID, [])

        # إذا لم تكن مفضل الأنمي → أرسل إشعار باسم عام
        if anime_title not in your_animes:
            embed = {
                "title": f"{anime_title} - الحلقة {episode_number}",
                "url": episode_link,
                "description": f"🎉 تم إصدار حلقة جديدة!\n{DISCORD_USER_NAME}",
                "color": 0x1ABC9C,
                "timestamp": datetime.utcnow().isoformat()
            }

            if image_url:
                embed["thumbnail"] = {"url": image_url}
                embed["image"] = {"url": image_url}

            payload = {
                "content": "🎥 حلقة جديدة!",
                "embeds": [embed],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 5,
                                "label": "🎬 مشاهدة الآن",
                                "url": episode_link
                            }
                        ]
                    }
                ]
            }

            try:
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
                if response.status_code in [200, 204]:
                    print(f"📢 تم إرسال الإشعار لك بصيغة الاسم {DISCORD_USER_NAME}.")
                else:
                    print(f"❌ فشل إرسال الإشعار باسم: {response.status_code} {response.text}")
            except Exception as e:
                print(f"❌ خطأ أثناء إرسال الإشعار باسم: {e}")
