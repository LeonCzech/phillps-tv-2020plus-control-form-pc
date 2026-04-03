import requests
from requests.auth import HTTPDigestAuth
import json
import base64
import hmac
import hashlib
import sys
import os

# Cross-platform keyboard support
try:
    import msvcrt  # Windows
    WINDOWS = True
except ImportError:
    import tty     # macOS/Linux
    import termios
    WINDOWS = False

# --- CONFIGURATION ---
PTA_MASTER_SECRET = "ZjkxY2IzYmI3OTY3YmU0MGY1YzdhZTM1YmY0NGE1YjU4Y2ZmYmI4ZGY4ZWIyMDZlYjljMTk2M2Y4YmI1ODljNQ=="
DEVICE_ID = "python_remote_v6"
AUTH_FILE = "tv_auth.json"

requests.packages.urllib3.disable_warnings()

def get_v6_signature(timestamp, pin):
    secret = base64.b64decode(PTA_MASTER_SECRET)
    message = (str(timestamp) + pin).encode('utf-8')
    sig_bytes = hmac.new(secret, message, hashlib.sha1).digest()
    sig_hex = sig_bytes.hex().lower()
    return base64.b64encode(sig_hex.encode('utf-8')).decode('utf-8')

def load_credentials():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    return None

def save_credentials(ip, auth_key):
    with open(AUTH_FILE, "w") as f:
        json.dump({"ip": ip, "auth_key": auth_key}, f)

def pair(tv_ip):
    base_url = f"https://{tv_ip}:1926/6"
    try:
        payload = {
            "scope": ["read", "write", "control"],
            "device": {"id": DEVICE_ID, "name": "Python Remote", "type": "Desktop"},
            "app": {"id": "org.droidtv.videofusion", "name": "Remote", "app_id": "1"}
        }
        r1 = requests.post(f"{base_url}/pair/request", json=payload, verify=False, timeout=5)
        data = r1.json()
        auth_key, timestamp = data['auth_key'], data['timestamp']
        
        print(f"\n[!] PIN required. Check the TV screen.")
        pin = input("Enter 4-digit PIN: ")
        signature = get_v6_signature(timestamp, pin)

        grant_payload = {
            "auth": {"auth_key": auth_key, "timestamp": timestamp, "signature": signature, "pin": pin},
            "device": {"id": DEVICE_ID, "name": "Python Remote", "type": "Desktop"}
        }

        r2 = requests.post(f"{base_url}/pair/grant", json=grant_payload, 
                           auth=HTTPDigestAuth(DEVICE_ID, auth_key), verify=False)

        if r2.status_code == 200:
            save_credentials(tv_ip, auth_key)
            print("[✔] Pairing Successful and Saved!")
            return auth_key
    except Exception as e:
        print(f"[!] Error: {e}")
    sys.exit(1)

def send_key(tv_ip, key, auth_pass):
    url = f"https://{tv_ip}:1926/6/input/key"
    try:
        requests.post(url, json={"key": key}, auth=HTTPDigestAuth(DEVICE_ID, auth_pass), verify=False, timeout=0.5)
    except: pass

def remote_loop(tv_ip, auth_pass):
    print(f"\n--- REMOTE ACTIVE (TV: {tv_ip}) ---")
    print("W/A/S/D: Arrows | F: OK | B: Back | H: Home | v/V: Vol | Q: Quit")
    mapping = {'w':'CursorUp','s':'CursorDown','a':'CursorLeft','d':'CursorRight','f':'Confirm','b':'Back','h':'Home','v':'VolumeDown','V':'VolumeUp'}

    if WINDOWS:
        while True:
            char = msvcrt.getch().decode('utf-8', errors='ignore')
            if char.lower() == 'q': break
            if char in mapping: send_key(tv_ip, mapping[char], auth_pass)
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                char = sys.stdin.read(1)
                if char.lower() == 'q': break
                if char in mapping: send_key(tv_ip, mapping[char], auth_pass)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

if __name__ == "__main__":
    creds = load_credentials()
    if creds:
        print(f"[*] Found saved credentials for {creds['ip']}")
        ip, token = creds['ip'], creds['auth_key']
    else:
        ip = input("Enter TV IP Address: ")
        token = pair(ip)
    
    remote_loop(ip, token)
