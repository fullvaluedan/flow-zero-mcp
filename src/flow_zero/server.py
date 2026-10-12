"""
FlowZero MCP Server
Connects Claude Desktop, Claude Code, Cursor, and other MCP clients to Google Flow
powered by Google Veo 3.1 & Omni Flash, utilizing active Google AI Pro/Ultra subscriptions.
Features smart daily credit tracking with 50% and 20% milestone alerts.
"""

from __future__ import annotations

import sys
import os
import json
import asyncio
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from mcp.server.mcpserver import MCPServer

DEFAULT_OUTPUT_DIR = str(Path.home() / "Videos" / "Flow")
TRACKER_FILE = Path.home() / ".flow_credits_tracker.json"

COST_CATALOG = {
    "veo-fast": 20,
    "veo-lite": 10,
    "veo-lite-lp": 10,
    "veo-quality": 40,
    "omni-flash": 20,
    "extend": 20,
    "image": 5,
}

mcp = MCPServer("flow-zero")

def _find_gflow() -> List[str]:
    """Finds the gflow executable command."""
    exe = shutil.which("gflow")
    if exe:
        return [exe]
    candidates = [
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\Scripts\gflow.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\Scripts\gflow.exe"),
        os.path.expanduser("~/.local/bin/gflow"),
        "/usr/local/bin/gflow",
    ]
    for c in candidates:
        if os.path.exists(c):
            return [c]
    return [sys.executable, "-m", "gflow_cli"]

class CreditTracker:
    @staticmethod
    def get_today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @classmethod
    def load(cls) -> Dict[str, Any]:
        if TRACKER_FILE.exists():
            try:
                with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("date") == cls.get_today_str():
                    return data
            except Exception:
                pass
        return {}

    @classmethod
    def save(cls, data: Dict[str, Any]):
        try:
            with open(TRACKER_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    async def get_or_sync(cls, force: bool = False, profile: str = "default") -> Dict[str, Any]:
        current = cls.load()
        if not force and current and "start_of_day_credits" in current:
            return current

        api_data = await _fetch_credits_raw(profile)
        if not api_data.get("authenticated"):
            return api_data

        credits = api_data.get("credits", 0)
        data = {
            "date": cls.get_today_str(),
            "email": api_data.get("email", ""),
            "tier": api_data.get("user_paygate_tier", "Google AI Pro"),
            "start_of_day_credits": credits,
            "current_credits": credits,
            "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generations_count": 0,
            "warned_50": False,
            "warned_20": False,
            "authenticated": True
        }
        cls.save(data)
        return data

    @classmethod
    def record_spend(cls, amount: int, gen_type: str = "video") -> Dict[str, Any]:
        data = cls.load()
        if not data:
            return {
                "start_of_day": amount,
                "current": 0,
                "spent": amount,
                "pct_remaining": 0.0,
                "warning_level": None
            }
        data["current_credits"] = max(0, data.get("current_credits", 0) - amount)
        data["generations_count"] = data.get("generations_count", 0) + 1

        start = data.get("start_of_day_credits", 1) or 1
        curr = data.get("current_credits", 0)
        pct = (curr / start) * 100

        warning_level = None
        if pct <= 20 and not data.get("warned_20"):
            data["warned_20"] = True
            warning_level = "20_percent"
        elif pct <= 50 and not data.get("warned_50"):
            data["warned_50"] = True
            warning_level = "50_percent"

        cls.save(data)
        return {
            "start_of_day": start,
            "current": curr,
            "spent": amount,
            "pct_remaining": round(pct, 1),
            "warning_level": warning_level
        }

async def _fetch_credits_raw(profile: str = "default") -> Dict[str, Any]:
    cmd = _find_gflow() + ["credits", "user", "--json"]
    if profile != "default":
        cmd.extend(["--profile", profile])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            if "No profiles found" in out_text or "No profiles found" in err_text:
                return {"authenticated": False, "error": "not_authenticated"}
            return {"authenticated": False, "error": err_text or out_text}

        data = json.loads(out_text)
        data["authenticated"] = True
        return data
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

def _format_not_authenticated_msg() -> str:
    return (
        "⚠️ **Google Flow Authentication Required**\n\n"
        "Your Google account is not currently linked or the session has expired.\n\n"
        "**To connect your Google account with your Google AI Pro subscription:**\n"
        "1. Open a terminal (PowerShell, Command Prompt, or Bash).\n"
        "2. Run the interactive sign-in command:\n"
        "   ```bash\n"
        "   flow-zero-login\n"
        "   ```\n"
        "   *(or: `python -m flow_zero.auth` / `gflow auth login --browser chrome`)*\n"
        "3. A Chrome window will open. Complete sign-in into your Google account.\n"
        "4. Your Google AI Pro credits and session will be immediately live in Claude!\n"
    )

@mcp.tool(
    name="flow_get_credits",
    description="Check your live Google Flow credit balance. Automatically syncs once daily; set force_refresh=True to force a live API poll."
)
async def flow_get_credits(force_refresh: bool = False, profile: str = "default") -> str:
    data = await CreditTracker.get_or_sync(force=force_refresh, profile=profile)
    if not data.get("authenticated"):
        return _format_not_authenticated_msg()

    start_credits = data.get("start_of_day_credits", 0)
    current_credits = data.get("current_credits", start_credits)
    tier = data.get("tier", "Google AI Pro")
    email = data.get("email", "Google Account")
    gens = data.get("generations_count", 0)
    pct_left = (current_credits / start_credits * 100) if start_credits > 0 else 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sync_note = "🔄 Live API Synced" if force_refresh else "📅 Today's Active Session Ledger"

    return (
        f"### 💳 Google Flow Daily Credit Status\n\n"
        f"- **Account:** `{email}`\n"
        f"- **Subscription Tier:** **{tier}**\n"
        f"- **Start of Day Baseline:** **{start_credits:,}** credits\n"
        f"- **Current Available Balance:** **{current_credits:,}** credits (**{pct_left:.1f}% remaining**)\n"
        f"- **Generations Completed Today:** `{gens}` clips\n"
        f"- **Estimated Veo Fast Clips Remaining:** ~`{current_credits // 20}` clips\n"
        f"- **Ledger Mode:** {sync_note} ({now_str})\n"
    )

@mcp.tool(
    name="flow_generate_video",
    description=(
        "Generate cinematic AI videos using Google Flow (Veo 3.1 & Omni Flash) with your Google AI Pro subscription. "
        "Supports vertical (9:16 Shorts/Reels/TikTok) and horizontal (16:9 Cinematic), durations 4s/6s/8s/10s, "
        "models (veo-fast, veo-quality, veo-lite, omni-flash), Text-to-Video and Image-to-Video. "
        "Features daily predictable credit ledger with 50% and 20% milestone alert banners!"
    )
)
async def flow_generate_video(
    prompt: str,
    orientation: str = "vertical",
    duration: int = 8,
    model: str = "veo-fast",
    mode: str = "t2v",
    initial_frame: Optional[str] = None,
    end_frame: Optional[str] = None,
    resolution: Optional[str] = None,
    output_dir: Optional[str] = None,
    output_filename: Optional[str] = None,
    count: int = 1
) -> str:
    norm_orient = orientation.lower().strip()
    if norm_orient in ["vertical", "portrait", "9:16", "short", "shorts", "tiktok", "reel"]:
        aspect = "9:16"
        orient_label = "Vertical (9:16 - Shorts / Reels / TikTok)"
    elif norm_orient in ["horizontal", "landscape", "16:9", "cinematic", "widescreen", "youtube"]:
        aspect = "16:9"
        orient_label = "Horizontal (16:9 - Cinematic Widescreen)"
    else:
        aspect = "9:16"
        orient_label = "Vertical (9:16)"

    valid_models = {
        "veo-fast": "veo-fast",
        "veo_fast": "veo-fast",
        "veo-lite": "veo-lite",
        "veo_lite": "veo-lite",
        "veo-quality": "veo-quality",
        "veo_quality": "veo-quality",
        "veo-lite-lp": "veo-lite-lp",
        "omni-flash": "omni-flash",
        "omni_flash": "omni-flash"
    }
    chosen_model = valid_models.get(model.lower().strip(), "veo-fast")

    if chosen_model == "omni-flash":
        dur = duration if duration in [4, 6, 8, 10] else 10
    else:
        dur = duration if duration in [4, 6, 8] else 8

    chosen_mode = mode.lower().strip()
    if initial_frame and chosen_mode != "i2v":
        chosen_mode = "i2v"

    target_out_dir = output_dir or DEFAULT_OUTPUT_DIR
    norm_out_dir = os.path.abspath(target_out_dir).replace("\\", "/")
    os.makedirs(norm_out_dir, exist_ok=True)

    ledger_data = await CreditTracker.get_or_sync()
    if not ledger_data.get("authenticated"):
        return _format_not_authenticated_msg()

    unit_cost = COST_CATALOG.get(chosen_model, 20)
    total_cost = unit_cost * min(max(1, count), 4)

    cmd = _find_gflow() + ["video"]
    if chosen_mode == "i2v":
        if not initial_frame or not os.path.exists(initial_frame):
            return f"❌ Error: Image-to-Video requires a valid `initial_frame` file path. Given: `{initial_frame}`"
        cmd.extend(["i2v", os.path.abspath(initial_frame), prompt])
        if end_frame and os.path.exists(end_frame):
            cmd.extend(["--end-frame", os.path.abspath(end_frame)])
    else:
        cmd.extend(["t2v", prompt])

    cmd.extend([
        "--aspect", aspect,
        "--model", chosen_model,
        "--duration", str(dur),
        "--count", str(min(max(1, count), 4)),
        "--out-dir", norm_out_dir,
        "--json"
    ])

    if resolution and resolution in ["360p", "720p"] and chosen_model == "omni-flash":
        cmd.extend(["--resolution", resolution])

    if output_filename:
        clean_name = output_filename if output_filename.endswith(".mp4") else f"{output_filename}.mp4"
        exact_path = os.path.join(norm_out_dir, clean_name).replace("\\", "/")
        cmd.extend(["-o", exact_path])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out_text = stdout.decode("utf-8", errors="replace").strip()
    err_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        return (
            f"### ❌ Google Flow Video Generation Failed\n\n"
            f"**Error Details:**\n```\n{err_text or out_text}\n```\n\n"
            f"*(Zero credits deducted — run aborted before submission.)*\n"
        )

    spend_info = CreditTracker.record_spend(total_cost, gen_type="video")
    curr_credits = spend_info.get("current", 0)
    pct_left = spend_info.get("pct_remaining", 0.0)
    warning_lvl = spend_info.get("warning_level")

    milestone_banner = ""
    if warning_lvl == "20_percent" or pct_left <= 20.0:
        milestone_banner = (
            "> 🚨 **CRITICAL CREDIT ALERT (20% RESERVE)**\n"
            f"> You are down to **{curr_credits:,} credits ({pct_left}%)** of your starting balance!\n"
            "> *Tip: Consider switching to `veo-lite` (10 credits) for draft iterations.*\n\n"
        )
    elif warning_lvl == "50_percent" or (pct_left <= 50.0 and pct_left > 20.0):
        milestone_banner = (
            "> ⚠️ **CREDIT MILESTONE WARNING (50% HALFWAY MARK)**\n"
            f"> You have consumed half your daily credits. **{curr_credits:,} credits ({pct_left}%)** remaining.\n\n"
        )

    video_files: List[str] = []
    try:
        res_json = json.loads(out_text)
        if isinstance(res_json, dict):
            if "files" in res_json and isinstance(res_json["files"], list):
                video_files = res_json["files"]
            elif "output" in res_json:
                video_files = [res_json["output"]]
    except Exception:
        found = re.findall(r'([A-Za-z]:\\[^`\r\n]+\.mp4|[A-Za-z]:/[^`\r\n]+\.mp4|/[^`\r\n]+\.mp4)', out_text)
        video_files = [f.replace("\\", "/") for f in found]

    if not video_files:
        try:
            mp4s = [
                os.path.join(norm_out_dir, f).replace("\\", "/")
                for f in os.listdir(norm_out_dir)
                if f.endswith(".mp4")
            ]
            if mp4s:
                mp4s.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                video_files = [mp4s[0]]
        except Exception:
            pass

    file_info_blocks = []
    for vf in video_files:
        norm_vf = vf.replace("\\", "/")
        fname = os.path.basename(norm_vf)
        size_mb = f"{os.path.getsize(norm_vf) / (1024*1024):.2f} MB" if os.path.exists(norm_vf) else "Unknown"
        file_info_blocks.append(
            f"- **File Name:** `{fname}` ({size_mb})\n"
            f"- **Local Path:** `{norm_vf}`\n"
            f"- **Direct Link:** [{fname}](file:///{norm_vf})"
        )

    files_text = "\n\n".join(file_info_blocks) if file_info_blocks else f"- Saved to `{norm_out_dir}`"

    return (
        f"{milestone_banner}"
        f"### 🎬 Google Flow Video Generated Successfully!\n\n"
        f"#### 💳 Daily Credit Tracker Ledger\n"
        f"- **Operation Cost:** -`{total_cost}` credits (`{chosen_model}`)\n"
        f"- **Balance Remaining:** **{curr_credits:,} credits ({pct_left}% left)**\n"
        f"- **Estimated Veo Fast Clips Remaining:** ~`{curr_credits // 20}` clips\n\n"
        f"#### 📹 Video Specifications\n"
        f"- **Prompt:** \"{prompt}\"\n"
        f"- **Orientation:** {orient_label}\n"
        f"- **Duration:** {dur} seconds\n"
        f"- **Model:** `{chosen_model}`\n"
        f"- **Mode:** `{chosen_mode.upper()}`\n\n"
        f"#### 📁 Output Media Files\n"
        f"{files_text}\n"
    )

@mcp.tool(
    name="flow_extend_video",
    description="Extend an existing Google Flow video by an extra 8 seconds with motion and audio continuity."
)
async def flow_extend_video(
    media_id: str,
    prompt: str,
    project_id: str,
    orientation: str = "vertical",
    output_file: Optional[str] = None
) -> str:
    aspect = "9:16" if "vert" in orientation.lower() or "9:16" in orientation else "16:9"

    ledger_data = await CreditTracker.get_or_sync()
    if not ledger_data.get("authenticated"):
        return _format_not_authenticated_msg()

    cmd = _find_gflow() + [
        "video", "extend",
        media_id, prompt,
        "--project", project_id,
        "--aspect", aspect,
        "--json"
    ]
    if output_file:
        cmd.extend(["-o", os.path.abspath(output_file)])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out_text = stdout.decode("utf-8", errors="replace").strip()
    err_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        return f"### ❌ Extend Video Failed\n\n```\n{err_text or out_text}\n```"

    spend_info = CreditTracker.record_spend(20, gen_type="extend")
    curr_credits = spend_info.get("current", 0)
    pct_left = spend_info.get("pct_remaining", 0.0)

    return (
        f"### 🎬 Video Extended Successfully (+8 Seconds)!\n\n"
        f"#### 💳 Daily Credit Tracker Ledger\n"
        f"- **Operation Cost:** -20 credits\n"
        f"- **Balance Remaining:** **{curr_credits:,} credits ({pct_left}% left)**\n\n"
        f"**Continuation Prompt:** \"{prompt}\"\n"
        f"**Aspect Ratio:** `{aspect}`\n"
    )

@mcp.tool(
    name="flow_generate_image",
    description="Generate images using Google Flow's Imagen / Nano Banana models (5 credits/image)."
)
async def flow_generate_image(
    prompt: str,
    aspect_ratio: str = "9:16",
    model: str = "nano2",
    count: int = 1,
    output_dir: Optional[str] = None
) -> str:
    target_out_dir = output_dir or DEFAULT_OUTPUT_DIR
    norm_out_dir = os.path.abspath(target_out_dir).replace("\\", "/")
    os.makedirs(norm_out_dir, exist_ok=True)

    ledger_data = await CreditTracker.get_or_sync()
    if not ledger_data.get("authenticated"):
        return _format_not_authenticated_msg()

    cost = 5 * min(max(1, count), 4)

    cmd = _find_gflow() + [
        "image", "t2i",
        prompt,
        "--aspect", aspect_ratio,
        "--model", model,
        "-n", str(min(max(1, count), 4)),
        "--out", norm_out_dir,
        "--json"
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out_text = stdout.decode("utf-8", errors="replace").strip()
    err_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        return f"### ❌ Image Generation Failed\n\n```\n{err_text or out_text}\n```"

    spend_info = CreditTracker.record_spend(cost, gen_type="image")
    curr_credits = spend_info.get("current", 0)

    found = re.findall(r'([A-Za-z]:\\[^`\r\n]+\.png|[A-Za-z]:/[^`\r\n]+\.png|/[^`\r\n]+\.png)', out_text)
    image_files = [f.replace("\\", "/") for f in found]
    links = "\n".join([f"- [{os.path.basename(f)}](file:///{f})" for f in image_files]) or f"- Files saved in `{norm_out_dir}`"

    return (
        f"### 🖼️ Google Flow Image Generated!\n\n"
        f"#### 💳 Daily Credit Tracker Ledger\n"
        f"- **Cost:** -{cost} credits\n"
        f"- **Balance Remaining:** **{curr_credits:,} credits**\n\n"
        f"**Prompt:** \"{prompt}\"\n"
        f"**Aspect Ratio:** `{aspect_ratio}`\n\n"
        f"#### 📁 Files:\n{links}\n"
    )

@mcp.tool(
    name="flow_list_models",
    description="List all available Google Flow video models (Veo 3.1 & Omni Flash) and image models, aspects, and durations."
)
async def flow_list_models() -> str:
    cmd = _find_gflow() + ["models", "--json"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out_text = stdout.decode("utf-8", errors="replace").strip()

    try:
        catalog = json.loads(out_text)
        video_md = "### 🎥 Video Models (Veo / Omni)\n\n| Model | Alias | Cost | Max Dur | Native Audio |\n|---|---|---|---|---|\n"
        for vm in catalog.get("video", {}).get("models", []):
            aliases = ", ".join(vm.get("aliases", []))
            alias_key = vm.get("aliases", [""])[0]
            cost = COST_CATALOG.get(alias_key, 20)
            max_d = f"{vm.get('max_duration', 8)}s"
            audio = "✅ Yes" if "omni" in vm.get("name", "") else "No"
            video_md += f"| `{vm.get('name')}` | `{aliases}` | ~{cost} cr | {max_d} | {audio} |\n"

        img_md = "\n### 🎨 Image Models (Imagen / Nano Banana)\n\n| Model | Alias | Cost |\n|---|---|---|\n"
        for im in catalog.get("image", {}).get("models", []):
            aliases = ", ".join(im.get("aliases", []))
            img_md += f"| `{im.get('name')}` | `{aliases}` | ~5 cr |\n"

        return (
            f"## 🎬 Google Flow Model Catalog\n\n"
            f"{video_md}\n"
            f"**Supported Video Aspect Ratios:**\n"
            f"- `9:16` (Vertical for Shorts, Reels, TikTok)\n"
            f"- `16:9` (Horizontal Cinematic Widescreen)\n\n"
            f"{img_md}\n"
            f"**Supported Image Aspect Ratios:** `9:16`, `16:9`, `1:1`, `4:3`, `3:4`\n"
        )
    except Exception:
        return f"```\n{out_text}\n```"

@mcp.tool(
    name="flow_auth_status",
    description="Check your Google Flow authentication status, connected Google account, and profile health."
)
async def flow_auth_status() -> str:
    data = await CreditTracker.get_or_sync()
    if not data.get("authenticated"):
        return _format_not_authenticated_msg()

    return (
        f"### 🟢 Google Flow Account Status: Active\n\n"
        f"- **Email:** `{data.get('email', 'N/A')}`\n"
        f"- **Plan Tier:** `{data.get('tier', 'Google AI Pro')}`\n"
        f"- **Today's Baseline:** `{data.get('start_of_day_credits', 0):,} credits`\n"
        f"- **Current Balance:** **{data.get('current_credits', 0):,} credits**\n"
        f"- **Status:** Verified & Ready\n"
    )

def main():
    asyncio.run(mcp.run_stdio_async())

if __name__ == "__main__":
    main()
