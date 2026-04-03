# JointSpace V6 CLI: Philips/TP Vision Secure Remote Client

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python-based CLI for controlling 2020+ Philips (TP Vision) Smart TVs. This project 
specifically bypasses the hardened "JointSpace V6" authentication layer that 
consistently triggers 401 Unauthorized errors in older libraries.

---

## !!! LEGAL DISCLAIMER & LIABILITY !!!
**I AM NOT RESPONSIBLE.** Use this software at your own risk.
1. This tool is NOT affiliated with, authorized, or endorsed by TP Vision or Philips.
2. The authentication logic and "Master Secret" were derived via REVERSE ENGINEERING 
   and decompilation of official APKs (philipstvapp2) for interoperability purposes.
3. Incorrect use of this API could theoretically lead to device lockout or network 
   instability. I provide zero warranty.
4. "JointSpace" and "Philips" are trademarks of their respective owners.

---
!!!ONLY TESTED ON MACOS!!!

## DEEP DIVE: REVERSE ENGINEERING THE V6 HANDSHAKE

### 1. The Decompilation Findings
Analysis of the official Philips TV Remote app (v2.x) revealed a massive shift in 
security architecture. While older TVs used simple JSON-RPC, 2020+ models (TPM211, 
TPM215, and OLED series) utilize a multi-layered stack:

* **Restlet Framework 2.3.12:** The Java-based REST engine on the TV that manages 
  the /6/ API. It is extremely strict regarding User-Agents and Header formatting.
* **AWS4Signer & Cognito:** The app contains full Amazon Web Services Signature V4 
  libraries. While used primarily for Alexa/Cloud sync, the local pairing logic 
  borrows the "Derived Key" philosophy from AWS.
* **AppUtils.getHMACSHA1:** This is the specific helper found in the APK that 
  generates the "local" signature required for the Grant phase.

### 2. The "Signature" Trap (Why your Curl failed)
The TV rejects the `pair/grant` request if the `signature` field in the JSON body 
is not mathematically perfect. The recipe discovered during decompilation is:

1. **The Secret:** An 88-character Base64 string hardcoded in the TVEngine.
2. **The Message:** A concatenation of the `timestamp` (from Step 1) and the `pin` 
   entered by the user.
3. **The Algorithm:** HMAC-SHA1 (Note: Even though SHA256 libraries are present, 
   local pairing still relies on SHA1).
4. **The Critical Encoding:** The HMAC result is converted to a LOWERCASE HEX 
   STRING. This Hex string is then BASE64 ENCODED.
   
   *Logic flow:* `HMAC-SHA1 -> Hex -> Base64`

Most 3rd-party attempts fail because they try to Base64 encode the raw binary 
HMAC, which the TV's Restlet server rejects as an invalid signature.

### 3. The Protocol (Port 1926 vs 58012)
While port `58012` is used for encrypted SSL socket streams (WoWLAN), the 
standard control remains on `1926`. However, the TV now requires **HTTP Digest 
Authentication** for every single call. In the "Grant" phase, the TV validates 
your `device_id` and uses the `auth_key` (generated in Step 1) as the Digest 
Password.

---

## FEATURES
- **Automated V6 Handshake:** Handles the complex Signature + Digest cycle.
- **Low-Level Key Simulation:** Sends raw KeyCodes (CursorUp, Confirm, etc.).
- **Raw Input Mapping:**
  - [W/A/S/D] -> D-Pad
  - [F]       -> OK / Confirm
  - [B]       -> Back
  - [H]       -> Home
  - [v / V]   -> Volume Down / Up
- **No-Enter Control:** Captures keystrokes instantly for a real remote feel.

---

## INSTALLATION & USAGE

1. **Clone Repo**
   `git clone https://github.com/LeonCzech/phillps-tv-controller.git`

1. **Install Dependencies:**
   `pip install requests`

2. **Run the Client:**
   `python3 main.py`

3. **Pairing:**
   Follow the prompts to enter the TV IP and the 4-digit PIN. The script will 
   automatically derive the V6 signature and establish a session.

---

## LICENSE
Distributed under the **MIT License**. See `LICENSE` for the full text.
