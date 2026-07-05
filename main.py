import asyncio, aiohttp, os, urllib.parse, re, random, binascii, uuid, time
from MedoSigner import Argus, Gorgon, Ladon, md5

# ─── Telegram Bot Config ───
TELEGRAM_BOT_TOKEN = "8848866254:AAFUKRg-W8ZHKCW_KkYgRzcn4EIdaIsfxiU"
TELEGRAM_CHAT_ID   = "8989271393"

async def send_to_telegram(message):
    """إرسال رسالة إلى بوت التيليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
    except Exception as e:
        print(f"[Telegram Error] {e}")

def Vals():
    ts = str(round(random.uniform(1.2, 1.6) * 1e8) * -1)
    return {
        "manifest_version_code": "330802", "_rticket": f"{ts}4632", "app_language": "ar",
        "app_type": "normal", "iid": str(random.randint(1, 10**19)), "channel": "googleplay",
        "device_type": "RMX3511", "language": "ar", "host_abi": "arm64-v8a", "locale": "ar",
        "resolution": "1080*2236", "openudid": binascii.hexlify(os.urandom(8)).decode(),
        "update_version_code": "330802", "ac2": "lte", "cdid": str(uuid.uuid4()), "sys_region": "IQ",
        "os_api": "33", "timezone_name": "Asia/Baghdad", "dpi": "360", "carrier_region": "IQ",
        "ac": "4g", "device_id": str(random.randint(1, 10**19)), "os_version": "13",
        "timezone_offset": "10800", "version_code": "330802", "app_name": "musically_go",
        "ab_version": "33.8.2", "version_name": "33.8.2", "device_brand": "realme",
        "op_region": "IQ", "ssmix": "a", "device_platform": "android", "build_number": "33.8.2",
        "region": "IQ", "aid": "1340", "ts": ts
    }, {
        'User-Agent': 'com.zhiliaoapp.musically/2023001020 (Linux; U; Android 13; ar; RMX3511; Build/TP1A.220624.014; Cronet/TTNetVersion:06d6a583 2023-04-17 QuicVersion:d298137e 2023-02-13)'}

def sign(params, payload=None, sec_device_id="", cookie=None, aid=1233, license_id=1611921764, 
         sdk_version_str="2.3.1.i18n", sdk_version=2, platform=19, unix=None):
    unix = unix or int(time.time())
    x_ss_stub = md5(payload.encode()).hexdigest() if payload else None
    return Gorgon(params, unix, payload, cookie).get_value() | {
        "x-ladon": Ladon.encrypt(unix, license_id, aid),
        "x-argus": Argus.get_sign(params, x_ss_stub, unix, platform, aid, license_id, sec_device_id, sdk_version_str, sdk_version)
    }

async def get_following(session, user_id, qu, lock, users, counter):
    """جلب قائمة المتابعين مع إرسال النتائج إلى Telegram"""
    token = None
    while True:
        try:
            p, h = Vals()
            signed = sign(params=urllib.parse.urlencode(p), payload="", cookie="")
            h.update({k: signed[k] for k in ['x-ss-req-ticket', 'x-argus', 'x-gorgon', 'x-khronos', 'x-ladon']})
            url = f'https://api16-normal-c-alisg.tiktokv.com/lite/v2/relation/following/list/?user_id={user_id}&count=50&source_type=1&request_tag_from=h5&{urllib.parse.urlencode(p)}'
            if token: 
                url += f"&page_token={urllib.parse.quote(token)}"
            async with session.get(url, headers=h) as r:
                data = await r.json()

            new_users = []
            for user in data.get("followings", []):
                username = user.get("unique_id")
                if username and username not in users:
                    async with lock:
                        counter[0] += 1
                        users.add(username)

                        if "_" not in username and len(username) > 7 and "." not in username and user.get("follower_count", 0) >= 1:
                            msg = f'{counter[0]} - {username} | {user.get("follower_count", 0)}'
                            print(msg)
                            new_users.append(username)
                            with open("tiklist.txt", "a", encoding="utf-8") as f:
                                f.write(username + '\n')

            # إرسال الدفعة الجديدة إلى Telegram
            if new_users:
                telegram_msg = "\n".join([f"@{u}" for u in new_users])
                await send_to_telegram(f"<b>✅ New Users Found:</b>\n{telegram_msg}")

            if not data.get("has_more") or not (token := data.get("next_page_token")):
                break
        except Exception as e:
            print(f"[Error] {e}")
            break

async def worker(session, qu, lock, users, counter):
    """الووركر - يتم إيقافه بـ Poison Pill (None)"""
    while True:
        try:
            user_id = await qu.get()
            if user_id is None:          # Poison pill
                qu.task_done()
                break
            await get_following(session, user_id, qu, lock, users, counter)
            qu.task_done()
        except Exception as e:
            print(f"[Worker Error] {e}")
            qu.task_done()

async def main():
    us = input('Enter Username: ')

    # ─── إنشاء المتغيرات داخل main() لتجنب "attached to a different loop" ───
    qu     = asyncio.Queue()
    lock   = asyncio.Lock()
    users  = set()
    counter = [0]          # list لتكون mutable داخل async

    async with aiohttp.ClientSession() as session:
        await send_to_telegram(f"<b>🚀 Starting scan for:</b> {us}")

        # جلب user_id من TikTok
        for username in (u.strip() for u in us.split(",") if u.strip()):
            try:
                async with session.get(f"https://www.tiktok.com/@{username}") as r:
                    text = await r.text()
                    if user_id := re.search(r'"id":"(\d+)"', text):
                        await qu.put(user_id.group(1))
            except Exception as e:
                print(f"[ID Error] {username}: {e}")

        # تشغيل 40 ووركر
        workers = [asyncio.create_task(worker(session, qu, lock, users, counter)) for _ in range(40)]

        await qu.join()

        # إرسال Poison Pills لإيقاف الووركرز
        for _ in range(40):
            await qu.put(None)

        await asyncio.gather(*workers)

        await send_to_telegram(f"<b>✅ Scan Complete!</b>\nTotal found: {counter[0]}\nSaved to tiklist.txt")

if __name__ == '__main__':
    asyncio.run(main())
