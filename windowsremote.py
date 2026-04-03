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
# This is the "Master Key" found in the Philips TV Engine decompilation.
# It is used for the HMAC-SHA1 signature required by JointSpace V6.
PTA_MASTER_SECRET = "ZjkxY2IzYmI3OTY3YmU0MGY1YzdhZTM1YmY0NGE1YjU4Y2ZmYmI4ZGY4ZWIyMDZlYjljMTk2M2Y4YmI1ODljNQ=="
DEVICE_ID = "python_remote_v6"
APP_ID = "org.droidtv.videofusion"

# Disable SSL warnings for the TV's self-signed certificate
requests.packages.urllib3.disable_warnings()

def get_v6_signature(timestamp, pin):
    """
    Implements the proprietary Philips V6 signature:
    HMAC-SHA1(MasterSecret, timestamp + pin) -> Lowercase Hex -> Base64
    """
    secret = base64.b64decode(PTA_MASTER_SECRET)
    message = (str(timestamp) + pin).encode('utf-8')
    
    # Calculate HMAC-SHA1
    sig_bytes = hmac.new(secret, message, hashlib.sha1).digest()
    
    # Convert to lowercase hex, then Base64 encode that hex string
    sig_hex = sig_bytes.hex().lower()
    return base64.b64encode(sig_hex.encode('utf-8')).decode('utf-8')

def pair(tv_ip):
    base_url = f"https://{tv_ip}:1926/6"
    print(f"[*] Requesting PIN from {tv_ip}...")
    
    try:
        payload = {
            "scope": ["read", "write", "control"],
            "device": {"id": DEVICE_ID, "name": "Python Remote", "type": "Desktop"},
            "app": {"id": APP_ID, "name": "Remote", "app_id": "1"}
        }
        r1 = requests.post(f"{base_url}/pair/request", json=payload, verify=False, timeout=5)
        data = r1.json()
        auth_key = data['auth_key']
        timestamp = data['timestamp']
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        sys.exit(1)

    print(f"\n[!] PIN required. Check the TV screen.")
    pin = input("Enter 4-digit PIN: ")

    signature = get_v6_signature(timestamp, pin)

    grant_payload = {
        "auth": {
            "auth_key": auth_key,
            "timestamp": timestamp,
            "signature": signature,
            "pin": pin
        },
        "device": {"id": DEVICE_ID, "name": "Python Remote", "type": "Desktop"}
    }

    print(f"[*] Sending Grant (Signature: {signature[:10]}...)")
    # Authentication uses DEVICE_ID as user and the Step 1 auth_key as password
    r2 = requests.post(f"{base_url}/pair/grant", 
                       json=grant_payload, 
                       auth=HTTPDigestAuth(DEVICE_ID, auth_key), 
                       verify=False)

    if r2.status_code == 200:
        print("[✔] Pairing Successful!")
        return auth_key
    else:
        print(f"[x] Pairing Failed ({r2.status_code}): {r2.text}")
        sys.exit(1)

def send_key(tv_ip, key, auth_pass):
    url = f"https://{tv_ip}:1926/6/input/key"
    try:
        requests.post(url, json={"key": key}, 
                      auth=HTTPDigestAuth(DEVICE_ID, auth_pass), 
                      verify=False, timeout=0.5)
    except:
        pass

def remote_loop(tv_ip, auth_pass):
    print("\n" + "="*30)
    print(" REMOTE CONTROL ACTIVE")
    print("="*30)
    print(" W/A/S/D : Arrows")
    print(" F       : OK / Confirm")
    print(" B       : Back")
    print(" H       : Home")
    print(" v       : Volume Down")
    print(" V (Cap) : Volume Up")
    print(" Q       : Quit")
    print("="*30)

    mapping = {
        'w': 'CursorUp', 's': 'CursorDown', 'a': 'CursorLeft', 'd': 'CursorRight',
        'f': 'Confirm', 'b': 'Back', 'h': 'Home', 'v': 'VolumeDown', 'V': 'VolumeUp'
    }

    if WINDOWS:
        while True:
            # msvcrt.getch() catches the key and returns bytes
            char_bytes = msvcrt.getch()
            try:
                char = char_bytes.decode('utf-8')
            except UnicodeDecodeError:
                continue

            if char.lower() == 'q': 
                break
            
            # Direct match (handles 'v' and 'V' separately)
            if char in mapping:
                send_key(tv_ip, mapping[char], auth_pass)
    else:
        # macOS / Linux (Unix) Raw Mode
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                char = sys.stdin.read(1)
                if char.lower() == 'q': 
                    break
                if char in mapping:
                    send_key(tv_ip, mapping[char], auth_pass)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    ip = input("Enter TV IP Address: ")
    auth_token = pair(ip)
    remote_loop(ip, auth_token)
