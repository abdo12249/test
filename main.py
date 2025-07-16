import cloudscraper
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime
import os
import base64
import requests
from notifier import send_discord_notification

# إعداد GitHub و Discord
access_token = os.getenv("ACCESS_TOKEN")

repo_name = "abdo12249/1"
remote_folder = "test1/episodes"

# إعدادات ملف السجل للأنميات المفقودة
repo_name_log = "abdo12249/test" # يمكن تغيير هذا المستودع إذا لزم الأمر
missing_anime_log_filename = "missing_anime_log.json"

BASE_URL = "https://4i.nxdwle.shop"
EPISODE_LIST_URL = BASE_URL + "/episode/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

scraper = cloudscraper.create_scraper()

def to_id_format(text):
    text = text.strip().lower()
    text = text.replace(":", "")
    text = re.sub(r"[^a-z0-9()!\- ]", "", text)
    return text.replace(" ", "-")

def get_episode_links():
    print("📄 تحميل صفحة الحلقات...")
    response = scraper.get(EPISODE_LIST_URL, headers=HEADERS)
    if response.status_code != 200:
        print("❌ فشل تحميل الصفحة")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    return [a.get("href") for a in soup.select(".episodes-card-title a") if a.get("href", "").startswith("http")]

def check_episode_on_github(anime_title):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(url, headers=headers)
    if response.status_code == 200:
        download_url = response.json().get("download_url")
        if download_url:
            r = scraper.get(download_url)
            if r.status_code == 200:
                return True, r.json()
        return True, None
    elif response.status_code == 404:
        return False, None
    else:
        return False, None

def get_episode_data(episode_url):
    response = scraper.get(episode_url, headers=HEADERS)
    if response.status_code != 200:
        return None, None, None, None
    soup = BeautifulSoup(response.text, "html.parser")
    h3 = soup.select_one("div.main-section h3")
    full_title = h3.get_text(strip=True) if h3 else "غير معروف"
    if "الحلقة" in full_title:
        parts = full_title.rsplit("الحلقة", 1)
        anime_title = parts[0].strip()
        episode_number = parts[1].strip()
    else:
        anime_title = full_title
        episode_number = "غير معروف"
    servers = []
    for a in soup.select("ul#episode-servers li a"):
        name = a.get_text(strip=True)
        data_url = a.get("data-ep-url")
        if isinstance(data_url, str):
            url = data_url.strip()
            if url.startswith("//"):
                url = "https:" + url
            servers.append({"serverName": name, "url": url})
    return anime_title, episode_number, full_title, servers

def log_missing_anime(anime_title, episode_link):
    """
    تسجيل الأنميات التي لم يكن لها ملف JSON موجود وتم إنشاؤه حديثًا.
    """
    api_url = f"https://api.github.com/repos/{repo_name_log}/contents/{missing_anime_log_filename}"
    headers = {"Authorization": f"token {access_token}"}

    # محاولة جلب ملف السجل الحالي
    response = scraper.get(api_url, headers=headers)
    log_data = []
    sha = None

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json().get("content")).decode("utf-8")
            log_data = json.loads(content_decoded)
        except (json.JSONDecodeError, TypeError):
            print("⚠️ فشل فك تشفير أو تحليل ملف السجل الحالي. سيتم إنشاء ملف جديد.")
            log_data = []
    elif response.status_code == 404:
        print(f"ℹ️ ملف السجل {missing_anime_log_filename} غير موجود على GitHub. سيتم إنشاؤه.")
    else:
        print(f"❌ فشل جلب ملف السجل من GitHub: {response.status_code} {response.text}")

    # إضافة الإدخال الجديد إذا لم يكن موجودًا بالفعل
    new_entry = {
        "anime_title": anime_title,
        "episode_link": episode_link,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # التحقق مما إذا كان الإدخال موجودًا بالفعل لتجنب التكرار
    # يمكن تعديل هذا الشرط ليكون أكثر تحديدًا إذا لزم الأمر
    if not any(item.get("anime_title") == anime_title and item.get("episode_link") == episode_link for item in log_data):
        log_data.append(new_entry)
        content_to_upload = json.dumps(log_data, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content_to_upload.encode("utf-8")).decode()

        payload = {
            "message": f"تحديث سجل الأنميات المفقودة: إضافة {anime_title}",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"✅ تم تحديث سجل الأنميات المفقودة في {missing_anime_log_filename} على GitHub.")
        else:
            print(f"❌ فشل رفع سجل الأنميات المفقودة إلى GitHub: {r.status_code} {r.text}")
    else:
        print(f"ℹ️ الأنمي '{anime_title}' موجود بالفعل في سجل الأنميات المفقودة. تم التخطي.")


def save_to_json(anime_title, episode_number, episode_title, servers):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    exists_on_github, github_data = check_episode_on_github(anime_title)

    ep_data = {
        "number": int(episode_number) if episode_number.isdigit() else episode_number,
        "title": f"الحلقة {episode_number}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "link": f"https://abdo12249.github.io/1/test1/المشاهده.html?id={anime_id}&episode={episode_number}",
        "image": f"https://abdo12249.github.io/1/images/{anime_id}.webp",
        "servers": servers
    }

    if not exists_on_github:
        print(f"🚀 إنشاء ملف جديد للأنمي: {filename}")
        new_data = {
            "animeTitle": anime_title,
            "episodes": [ep_data]
        }
        content = json.dumps(new_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode()).decode()
        payload = {
            "message": f"إنشاء ملف {filename} مع الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"✅ تم إنشاء الملف ورفع البيانات على GitHub.")
            send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
            # تسجيل الأنمي في ملف السجل الجديد
            log_missing_anime(anime_title, ep_data["link"])
        else:
            print(f"❌ فشل إنشاء الملف على GitHub: {r.status_code} {r.text}")
        return

    if github_data is None:
        print("⚠️ لم أتمكن من تحميل محتوى الملف من GitHub.")
        return

    updated = False
    found = False
    for i, ep in enumerate(github_data["episodes"]):
        if str(ep["number"]) == str(ep_data["number"]):
            found = True
            if ep["servers"] != ep_data["servers"]:
                github_data["episodes"][i] = ep_data
                updated = True
                print(f"🔄 تم تحديث الحلقة {episode_number} لأن السيرفرات تغيرت.")
                send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
            else:
                print(f"⚠️ الحلقة {episode_number} موجودة بنفس البيانات، تم تخطيها.")
            break
    if not found:
        github_data["episodes"].append(ep_data)
        updated = True
        print(f"➕ تم إضافة الحلقة {episode_number} الجديدة.")
        send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
    if updated:
        content = json.dumps(github_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode()).decode()
        sha_response = scraper.get(api_url, headers=headers)
        sha = sha_response.json().get("sha") if sha_response.status_code == 200 else None
        payload = {
            "message": f"تحديث {filename} - الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha
        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"🚀 تم رفع التحديث إلى GitHub بنجاح.")
        else:
            print(f"❌ فشل رفع التحديث إلى GitHub: {r.status_code} {r.text}")

# التنفيذ
all_links = get_episode_links()

for idx, link in enumerate(all_links):
    print(f"\n🔢 حلقة {idx+1}/{len(all_links)}")
    anime_name, episode_number, full_title, server_list = get_episode_data(link)
    if anime_name and server_list:
        save_to_json(anime_name, episode_number, full_title, server_list)
    else:
        print("❌ تخطيت الحلقة بسبب خطأ.")
    time.sleep(1)
