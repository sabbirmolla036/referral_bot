import cloudscraper
import random
import string
import base64
import time
import threading
import os
from queue import Queue

# === Config ===
THREADS = 40
RETRY_LIMIT = 5
BATCH_SIZE = 40
EMAIL_FILE = "emails.txt"
EMAIL_COUNT = 1_000_000

# === Email Storage ===
email_list = []
email_index = 0
email_lock = threading.Lock()

# === Random Generators ===
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def generate_emails():
    print(f"📤 Generating {EMAIL_COUNT} emails...")
    with open(EMAIL_FILE, "w") as f:
        for _ in range(EMAIL_COUNT):
            first = random_string()
            last = random_string()
            number = random.randint(100, 999)
            email = f"{first}.{last}{number}@gmail.com"
            f.write(email + "\n")
    print(f"✅ Saved to {EMAIL_FILE}")

def load_emails():
    global email_list
    if not os.path.exists(EMAIL_FILE):
        generate_emails()

    with open(EMAIL_FILE) as f:
        email_list = [line.strip() for line in f if line.strip()]
    random.shuffle(email_list)
    print(f"📨 Loaded {len(email_list)} emails.")

def get_next_email():
    global email_index
    with email_lock:
        if email_index < len(email_list):
            email = email_list[email_index]
            email_index += 1
            return email
        else:
            return None

def random_name():
    return random_string(6).capitalize(), random_string(8).capitalize()

def random_password(min_len=8, max_len=12):
    chars = string.ascii_letters + string.digits + "!@#$%"
    length = random.randint(min_len, max_len)
    return ''.join(random.choices(chars, k=length))

def decode_ref(b64):
    try:
        return base64.b64decode(b64).decode().strip()
    except Exception as e:
        print(f"Decode error: {e}")
        return None

# === Registration Task ===
def register_task(ref_code, queue, scraper):
    while not queue.empty():
        try:
            _ = queue.get_nowait()
        except:
            return

        ref_url = f"https://aetheris.company/register?ref={ref_code}"

        try:
            scraper.get(ref_url, timeout=30)
        except Exception as e:
            print(f"❌ Failed to load referral page: {e}")
            queue.task_done()
            time.sleep(2)
            continue

        first, last = random_name()
        email = get_next_email()
        if not email:
            print("🚫 No more emails left.")
            queue.task_done()
            return
        password = random_password()

        payload = {
            "email": email,
            "first": first,
            "last": last,
            "password": password,
            "password2": password,
            "ref": ref_code
        }

        headers = {
            "Origin": "https://aetheris.company",
            "Referer": ref_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }

        for _ in range(RETRY_LIMIT):
            try:
                res = scraper.post("https://aetheris.company/api/reg", json=payload, headers=headers, timeout=30)
                if res.status_code == 200 and "token" in res.text:
                    print(f"✅ Registered: {email} | Password: {password}")
                    break
                else:
                    print(f"❌ Failed ({res.status_code}): {res.text[:100]}...")
            except Exception as e:
                print(f"❌ Exception: {e}")
            time.sleep(random.uniform(1, 3))
        else:
            print(f"❌ Skipped: {email}")

        queue.task_done()
        time.sleep(random.uniform(1, 2))

# === Batch Runner ===
def run_batch(ref_code, scraper):
    queue = Queue()
    for _ in range(BATCH_SIZE):
        queue.put(None)

    threads = []
    for _ in range(THREADS):
        t = threading.Thread(target=register_task, args=(ref_code, queue, scraper))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

# === Main Entry Point ===
if __name__ == "__main__":
    print("\n🌲 FOREST ARMY — Referral Bot with Email Generator")

    try:
        with open("code.txt") as f:
            raw_codes = [line.strip() for line in f if line.strip()]
            codes = [decode_ref(code) for code in raw_codes if decode_ref(code)]
    except FileNotFoundError:
        print("❌ code.txt not found.")
        exit()

    if not codes:
        print("❌ No valid referral codes found.")
        exit()

    load_emails()

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    print("🔌 Proxy Mode: OFF")

    try:
        while True:
            for code in codes:
                print(f"\n🚀 New batch for referral code: {code}")
                run_batch(code, scraper)
                time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
