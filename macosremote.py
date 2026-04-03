import requests
from requests.auth import HTTPDigestAuth
import json
import base64
import hmac
import hashlib
import sys
import tty
import termios
import uuid

# --- CONFIG ---
PTA_MASTER_SECRET = "ZjkxY2IzYmI3OTY3YmU0MGY1YzdhZTM1YmY0NGE1YjU4Y2ZmYmI4ZGY4ZWIyMDZlYjljMTk2M2Y4YmI1ODljNQ=="
DEVICE_ID = f"mac_{uuid.uuid4().hex[:8]}"

requests.packages.urllib3.disable_warnings()

def get_v6_signature(timestamp, pin):
    secret = base64.b64decode(PTA_MASTER_SECRET)
    message = (str(timestamp) + pin).encode('utf-8')
    sig_bytes = hmac.new(secret, message, hashlib.sha1).digest()
    sig_hex = sig_bytes.hex().lower()
    return base64.b64encode(sig_hex.encode('utf-8')).decode('utf-8')

def pair(tv_ip):
    base_url = f"https://{tv_ip}:1926/6"
    print(f"[*] New Session ID: {DEVICE_ID}")
    try:
        payload = {
            "scope": ["read", "write", "control"],
            "device": {"id": DEVICE_ID, "name": "MacRemote", "type": "Desktop"},
            "app": {"id": "org.droidtv.videofusion", "name": "Remote", "app_id": "1"}
        }
        r1 = requests.post(f"{base_url}/pair/request", json=payload, verify=False, timeout=5)
        data = r1.json()
        auth_key, timestamp = data['auth_key'], data['timestamp']
        
        pin = input("\n[!] Enter PIN from TV screen: ")
        signature = get_v6_signature(timestamp, pin)

        grant_payload = {
            "auth": {"auth_key": auth_key, "timestamp": timestamp, "signature": signature, "pin": pin},
            "device": {"id": DEVICE_ID, "name": "MacRemote", "type": "Desktop"}
        }

        r2 = requests.post(f"{base_url}/pair/grant", json=grant_payload, 
                           auth=HTTPDigestAuth(DEVICE_ID, auth_key), verify=False)

        if r2.status_code == 200:
            print("[✔] Pairing Successful!")
            return auth_key
    except Exception as e: print(f"[!] Error: {e}")
    sys.exit(1)

def send_key(tv_ip, key, auth_pass):
    url = f"https://{tv_ip}:1926/6/input/key"
    try:
        requests.post(url, json={"key": key}, auth=HTTPDigestAuth(DEVICE_ID, auth_pass), verify=False, timeout=0.5)
    except: pass

def remote_loop(tv_ip, auth_pass):
    print("\n" + "="*45)
    print("        PHILIPS TV REMOTE: MAC SESSION")
    print("="*45)
    print(" [W] Up          [F] OK / Confirm")
    print(" [S] Down        [B] Back / Return")
    print(" [A] Left        [H] Home Menu")
    print(" [D] Right       [Q] Quit Script")
    print("-" * 45)
    print(" [v] Vol Down    [V] Vol Up (Shift+V)")
    print("="*45)

    mapping = {
        'w':'CursorUp', 's':'CursorDown', 'a':'CursorLeft', 'd':'CursorRight',
        'f':'Confirm',  'b':'Back',       'h':'Home',       'v':'VolumeDown', 'V':'VolumeUp'
    }

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            char = sys.stdin.read(1)
            if char.lower() == 'q': break
            if char in mapping:
                send_key(tv_ip, mapping[char], auth_pass)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    
    print("\n[!] Remote Session Closed.")

if __name__ == "__main__":
    ip = input("Enter TV IP: ")
    token = pair(ip)
    remote_loop(ip, token)
