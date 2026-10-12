"""
Interactive Google Flow Authentication Helper for FlowZero MCP.
Launches browser sign-in to capture the session for your Google AI Pro/Ultra subscription.
"""

import sys
import subprocess
import json
import shutil
import os

def find_gflow() -> str:
    exe = shutil.which("gflow")
    if exe:
        return exe
    # Common locations on Windows / Linux / macOS
    candidates = [
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\Scripts\gflow.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\Scripts\gflow.exe"),
        os.path.expanduser("~/.local/bin/gflow"),
        "/usr/local/bin/gflow",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return sys.executable + " -m gflow_cli"

def main():
    print("=" * 68)
    print(" 🎬 FlowZero MCP: Google Flow Authentication Helper")
    print("=" * 68)
    print("\nThis will open Google Chrome to sign into your Google account")
    print("at flow.google.com using your Google AI Pro / Ultra subscription.\n")

    gflow_cmd = find_gflow()
    base_cmd = [gflow_cmd] if " " not in gflow_cmd else gflow_cmd.split()

    try:
        login_cmd = base_cmd + ["auth", "login", "--browser", "chrome"]
        print(f"Launching login via: {' '.join(login_cmd)} ...\n")
        res = subprocess.run(login_cmd)

        if res.returncode != 0:
            print(f"\n❌ Login process exited with code {res.returncode}.")
            sys.exit(res.returncode)

        print("\n✅ Authentication completed! Verifying Google Flow session...\n")
        
        check_cmd = base_cmd + ["credits", "user", "--json"]
        check_res = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if check_res.returncode == 0:
            try:
                data = json.loads(check_res.stdout.strip())
                print("=" * 68)
                print("🎉 Google Flow Connection Verified!")
                print("=" * 68)
                print(f"Account Email  : {data.get('email', 'N/A')}")
                print(f"Subscription   : {data.get('user_paygate_tier', 'Google AI Pro')}")
                print(f"Total Credits  : {data.get('credits', 'N/A'):,}")
                if data.get('subscription_credits'):
                    print(f"Sub Pool       : {data.get('subscription_credits'):,}")
                print("=" * 68)
                print("\nYou can now restart Claude Desktop and start generating AI videos!")
            except Exception:
                print(check_res.stdout)
        else:
            print(f"⚠️ Verification check returned:\n{check_res.stderr or check_res.stdout}")

    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
