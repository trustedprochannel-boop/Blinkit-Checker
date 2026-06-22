import os
import random
import string
import time
import uuid
from flask import Flask, request, jsonify
from curl_cffi import requests as cffi_requests

app = Flask(__name__)

BASE_URL = "https://api2.grofers.com"
USER_AGENTS = [
    "com.grofers.customerapp/280170954 (Linux; U; Android 15; en_IN; Pixel 9a; Build/BD4A.250505.003; Cronet/147.0.7727.49)",
    "com.grofers.customerapp/280170954 (Linux; U; Android 14; en_IN; Samsung SM-S911B; Build/BWK7; Cronet/147.0.7727.49)",
    "com.grofers.customerapp/280170954 (Linux; U; Android 13; en_IN; OnePlus CPH2411; Build/MT2111; Cronet/147.0.7727.49)",
]

IMPERSONATE_PROFILES = ["chrome110", "chrome116", "chrome120", "chrome124"]
PROXY_URL = os.environ.get("PROXY_URL")

def generate_registration_id():
    prefix = "".join(random.choices(string.ascii_letters + string.digits + "_-", k=22))
    suffix = "".join(random.choices(string.ascii_letters + string.digits + "_-", k=140))
    return f"{prefix}:APA91b{suffix}"

def check_blinkit(phone: str):
    last_error = ""

    for attempt in range(3):
        if attempt > 0:
            time.sleep(2)

        device_id = "".join(random.choices("0123456789abcdef", k=16))
        advertising_id = str(uuid.uuid4())
        user_agent = random.choice(USER_AGENTS)
        session_uuid = str(uuid.uuid4())
        lat = str(25.2730 + random.uniform(-0.01, 0.01))
        lon = str(82.9638 + random.uniform(-0.01, 0.01))
        registration_id = generate_registration_id()
        profile = random.choice(IMPERSONATE_PROFILES)

        headers = {
            "host_app": "blinkit",
            "version_name": "17.95.4",
            "app_client": "consumer_android",
            "app_version": "80170954",
            "auth_key": "45bff2b1437ff764d5e5b9b292f9771428e18fc40b7f3b7303d196ea84ab4341",
            "lat": lat,
            "lon": lon,
            "session_uuid": session_uuid,
            "device_id": device_id,
            "advertising_id": advertising_id,
            "registration_id": registration_id,
            "user-agent": user_agent,
        }

        data = {
            "country_code": "91",
            "otp_mode": "WHATSAPP",
            "user_phone": phone,
            "build_variant": "release",
        }

        try:
            proxies = {"https": PROXY_URL, "http": PROXY_URL} if PROXY_URL else None
            session = cffi_requests.Session(impersonate=profile, proxies=proxies)
            resp = session.post(f"{BASE_URL}/v2/accounts/", headers=headers, data=data, timeout=15)
            text = resp.text

            if resp.status_code == 429:
                last_error = f"rate_limited (attempt {attempt + 1})"
                continue

            if resp.status_code >= 400:
                last_error = f"http_{resp.status_code}: {text[:200]}"
                continue

            if "blocked" in text.lower():
                return {"status": "banned", "raw": text}

            if '"success":true' in text or '"success": true' in text:
                if '"action":"signup"' in text or '"action": "signup"' in text:
                    return {"status": "new", "raw": text}
                elif '"action":"login"' in text or '"action": "login"' in text:
                    return {"status": "old", "raw": text}
                else:
                    return {"status": "unknown", "raw": text}
            else:
                return {"status": "error", "raw": text}

        except Exception as e:
            last_error = f"attempt {attempt + 1} error: {str(e)}"
            continue

    return {"status": "error", "raw": last_error}

@app.route('/blinkit')
def blinkit():
    mobile = request.args.get('number', '')
    if mobile == 'test':
        return jsonify({"status": "website working"})
    if not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"error": "invalid_number"}), 400
    result = check_blinkit(mobile)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
