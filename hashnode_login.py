"""
Extracts your Hashnode session cookies from your real Chrome browser
and saves them for Playwright to use. Run this ONCE.

IMPORTANT: Close ALL Chrome windows before running this script!
"""
import os, json, browser_cookie3

save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                          "browser_profiles", "hashnode_cookies.json")

os.makedirs(os.path.dirname(save_path), exist_ok=True)

print("="*60)
print("[!] HASHNODE COOKIE EXTRACTOR")
print("[!] Extracting your Hashnode session from Chrome...")
print("[!] Make sure you are logged into Hashnode in Chrome!")
print("="*60)

try:
    # Extract all cookies from Chrome for hashnode.com
    cj = browser_cookie3.chrome(domain_name='.hashnode.com')
    
    cookies = []
    for cookie in cj:
        cookies.append({
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "secure": bool(cookie.secure),
            "httpOnly": False,
            "sameSite": "Lax"
        })
    
    if not cookies:
        print("\n[-] No Hashnode cookies found in Chrome!")
        print("[-] Please make sure you are LOGGED IN to Hashnode in Chrome first.")
    else:
        with open(save_path, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"\n[+] SUCCESS! Found {len(cookies)} cookies.")
        print(f"[+] Saved to: {save_path}")
        print("[+] You can now run the execution router - Hashnode will work automatically!")
        
except Exception as e:
    print(f"\n[-] Error extracting cookies: {e}")
    print("[-] Try closing ALL Chrome windows first, then run this script again.")
