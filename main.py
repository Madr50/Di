import asyncio, aiohttp, os, urllib.parse, re, random, binascii, uuid, time
from MedoSigner import Argus, Gorgon, Ladon, md5
us = input('Enter Username: ')
a, users, qu, lock = 0, set(), asyncio.Queue(), asyncio.Lock()
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
async def get_following(session, user_id):
    global a, users
    token = None
    while True:
        try:
            p, h = Vals()
            signed = sign(params=urllib.parse.urlencode(p), payload="", cookie="")
            h.update({k: signed[k] for k in ['x-ss-req-ticket', 'x-argus', 'x-gorgon', 'x-khronos', 'x-ladon']})
            url = f'https://api16-normal-c-alisg.tiktokv.com/lite/v2/relation/following/list/?user_id={user_id}&count=50&source_type=1&request_tag_from=h5&{urllib.parse.urlencode(p)}'
            if token: url += f"&page_token={urllib.parse.quote(token)}"
            async with session.get(url, headers=h) as r:
                data = await r.json()
            for user in data.get("followings", []):
                if (username := user.get("unique_id")) and username not in users:
                    async with lock:
                        a += 1
                        users.add(username)
                        
                        if "_" not in username and len(username) > 7 and "." not in username and user.get("follower_count", 0) >= 1:
	                        print(f'{a} - {username} | {user.get("follower_count", 0)}')
	                        with open("tiklist.txt", "a", encoding="utf-8") as f:
	                            f.write(username + '\n')
            if not data.get("has_more") or not (token := data.get("next_page_token")):
                break
        except Exception:
            break
async def worker(session):
    while True:
            await get_following(session, await qu.get())
            qu.task_done()
async def main():
    async with aiohttp.ClientSession() as session:
        for username in (u.strip() for u in us.split(",") if u.strip()):
            async with session.get(f"https://www.tiktok.com/@{username}") as r:
                if user_id := re.search(r'"id":"(\d+)"', await r.text()):
                    await qu.put(user_id.group(1))
        await asyncio.gather(*(worker(session) for _ in range(40)), qu.join())

if __name__ == '__main__':
    asyncio.run(main())
