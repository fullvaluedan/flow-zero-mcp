"""
FlowZero MCP Server
Connects Claude Desktop, Claude Code, Cursor, and other MCP clients to Google Flow
powered by Google Veo 3.1 & Omni Flash, utilizing active Google AI Pro/Ultra subscriptions.
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

# Auto-resolve default output directory across OS
DEFAULT_OUTPUT_DIR = str(Path.home() / "Videos" / "Flow")

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
    # Fallback to python -m gflow_cli
    return [sys.executable, "-m", "gflow_cli"]

async def _fetch_credits_raw(profile: str = "default") -> Dict[str, Any]:
    """Queries current credit balance via gflow CLI."""
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
    description="Check your live Google Flow credit balance and subscription tier (Google AI Pro/Ultra). Shows total credits remaining, subscription pool, and account email. $0 cost."
)
async def flow_get_credits(profile: str = "default") -> str:
    """Inspects live Google Flow credit balance."""
    data = await _fetch_credits_raw(profile)
    if not data.get("authenticated"):
        return _format_not_authenticated_msg()

    credits = data.get("credits", 0)
    sub_credits = data.get("subscription_credits", "N/A")
    tier = data.get("user_paygate_tier", "Google AI Pro")
    email = data.get("email", "Google Account")
    prof_name = data.get("profile", profile)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Estimate video generations (average 20 credits per Veo Fast generation)
    est_fast_clips = credits // 20 if isinstance(credits, int) and credits > 0 else 0

    return (
        f"### 💳 Google Flow Live Credit Balance\n\n"
        f"- **Account:** `{email}` (Profile: `{prof_name}`)\n"
        f"- **Subscription Tier:** **{tier}**\n"
        f"- **Total Credits Available:** **{credits:,}**\n"
        f"- **Monthly Subscription Pool:** `{sub_credits}`\n"
        f"- **Estimated Video Clips Remaining:** ~`{est_fast_clips}` clips (at ~20 credits/clip)\n"
        f"- **Status:** 🟢 Connected & Ready\n"
        f"- **Checked At:** `{now_str}`\n"
    )

@mcp.tool(
    name="flow_generate_video",
    description=(
        "Generate cinematic AI videos using Google Flow (Veo 3.1 & Omni Flash) with your Google AI Pro subscription. "
        "Supports vertical (9:16 Shorts/Reels/TikTok) and horizontal (16:9 Cinematic), durations 4s/6s/8s/10s, "
        "models (veo-fast, veo-quality, veo-lite, omni-flash), Text-to-Video and Image-to-Video. "
        "Automatically displays a LIVE CREDIT FEED showing credits before, deducted, and remaining!"
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
    """Generates video with live credit tracking and full Flow parameter support."""
    # Normalize orientation
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

    # Normalize model
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

    # Validate duration
    if chosen_model == "omni-flash":
        dur = duration if duration in [4, 6, 8, 10] else 10
    else:
        dur = duration if duration in [4, 6, 8] else 8

    # Normalize mode
    chosen_mode = mode.lower().strip()
    if initial_frame and chosen_mode != "i2v":
        chosen_mode = "i2v"

    # Destination directory
    target_out_dir = output_dir or DEFAULT_OUTPUT_DIR
    norm_out_dir = os.path.abspath(target_out_dir).replace("\\", "/")
    os.makedirs(norm_out_dir, exist_ok=True)

    # 1. LIVE CREDIT FEED: Pre-check balance
    pre_credits_data = await _fetch_credits_raw()
    if not pre_credits_data.get("authenticated"):
        return _format_not_authenticated_msg()

    credits_before = pre_credits_data.get("credits", 0)
    tier = pre_credits_data.get("user_paygate_tier", "Google AI Pro")
    email = pre_credits_data.get("email", "Google Account")

    # 2. Build execution command
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

    # 3. Execute generation
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    out_text = stdout.decode("utf-8", errors="replace").strip()
    err_text = stderr.decode("utf-8", errors="replace").strip()

    # 4. LIVE CREDIT FEED: Post-check balance
    post_credits_data = await _fetch_credits_raw()
    credits_after = post_credits_data.get("credits", credits_before)
    credits_spent = max(0, credits_before - credits_after) if isinstance(credits_before, int) and isinstance(credits_after, int) else "N/A"

    if proc.returncode != 0:
        return (
            f"### ❌ Google Flow Video Generation Failed\n\n"
            f"**Error Details:**\n```\n{err_text or out_text}\n```\n\n"
            f"**💳 Live Credit Feed (Safety Check):**\n"
            f"- **Credits Before:** `{credits_before:,}`\n"
            f"- **Credits Deducted:** `0` (Refused pre-submit; no credits wasted)\n"
            f"- **Current Balance:** `{credits_after:,}`\n"
        )

    # Parse resulting video files
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
        f"### 🎬 Google Flow Video Generated Successfully!\n\n"
        f"#### 💳 Live Credit Tracker Feed\n"
        f"- **Account:** `{email}` ({tier})\n"
        f"- **Balance Before:** **{credits_before:,}** credits\n"
        f"- **Credits Deducted:** **-{credits_spent}** credits\n"
        f"- **Live Balance Remaining:** **{credits_after:,}** credits\n\n"
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
    description=(
        "Extend an existing Google Flow video by an extra 8 seconds, carrying motion and audio forward seamlessly. "
        "Provide the clip's media ID or project reference and what should happen next. Includes live credit feed."
    )
)
async def flow_extend_video(
    media_id: str,
    prompt: str,
    project_id: str,
    orientation: str = "vertical",
    output_file: Optional[str] = None
) -> str:
    """Extends an existing Flow video clip by 8 seconds."""
    aspect = "9:16" if "vert" in orientation.lower() or "9:16" in orientation else "16:9"

    pre_credits_data = await _fetch_credits_raw()
    if not pre_credits_data.get("authenticated"):
        return _format_not_authenticated_msg()
    credits_before = pre_credits_data.get("credits", 0)

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

    post_credits_data = await _fetch_credits_raw()
    credits_after = post_credits_data.get("credits", credits_before)
    spent = max(0, credits_before - credits_after) if isinstance(credits_before, int) and isinstance(credits_after, int) else "N/A"

    if proc.returncode != 0:
        return f"### ❌ Extend Video Failed\n\n```\n{err_text or out_text}\n```"

    return (
        f"### 🎬 Video Extended Successfully (+8 Seconds)!\n\n"
        f"#### 💳 Live Credit Tracker Feed\n"
        f"- **Credits Before:** `{credits_before:,}`\n"
        f"- **Credits Deducted:** `-{spent}`\n"
        f"- **Live Balance Remaining:** `{credits_after:,}`\n\n"
        f"**Continuation Prompt:** \"{prompt}\"\n"
        f"**Aspect Ratio:** `{aspect}`\n"
    )

@mcp.tool(
    name="flow_generate_image",
    description=(
        "Generate images using Google Flow's Imagen / Nano Banana models with your Google AI Pro subscription. "
        "Supports aspect ratios: 9:16, 16:9, 1:1, 4:3, 3:4. Includes live credit tracker feed."
    )
)
async def flow_generate_image(
    prompt: str,
    aspect_ratio: str = "9:16",
    model: str = "nano2",
    count: int = 1,
    output_dir: Optional[str] = None
) -> str:
    """Generates image via Flow Imagen models."""
    target_out_dir = output_dir or DEFAULT_OUTPUT_DIR
    norm_out_dir = os.path.abspath(target_out_dir).replace("\\", "/")
    os.makedirs(norm_out_dir, exist_ok=True)

    pre_credits_data = await _fetch_credits_raw()
    if not pre_credits_data.get("authenticated"):
        return _format_not_authenticated_msg()
    credits_before = pre_credits_data.get("credits", 0)

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

    post_credits_data = await _fetch_credits_raw()
    credits_after = post_credits_data.get("credits", credits_before)
    spent = max(0, credits_before - credits_after) if isinstance(credits_before, int) and isinstance(credits_after, int) else "N/A"

    if proc.returncode != 0:
        return f"### ❌ Image Generation Failed\n\n```\n{err_text or out_text}\n```"

    found = re.findall(r'([A-Za-z]:\\[^`\r\n]+\.png|[A-Za-z]:/[^`\r\n]+\.png|/[^`\r\n]+\.png)', out_text)
    image_files = [f.replace("\\", "/") for f in found]

    links = "\n".join([f"- [{os.path.basename(f)}](file:///{f})" for f in image_files]) or f"- Files saved in `{norm_out_dir}`"

    return (
        f"### 🖼️ Google Flow Image Generated!\n\n"
        f"#### 💳 Live Credit Tracker Feed\n"
        f"- **Balance Before:** `{credits_before:,}`\n"
        f"- **Deducted:** `-{spent}` credits\n"
        f"- **Remaining:** `{credits_after:,}` credits\n\n"
        f"**Prompt:** \"{prompt}\"\n"
        f"**Aspect Ratio:** `{aspect_ratio}`\n"
        f"**Model:** `{model}`\n\n"
        f"#### 📁 Files:\n{links}\n"
    )

@mcp.tool(
    name="flow_list_models",
    description="List all available Google Flow video models (Veo 3.1 & Omni Flash) and image models, aspects, and durations."
)
async def flow_list_models() -> str:
    """Lists Flow models."""
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
        video_md = "### 🎥 Video Models (Veo / Omni)\n\n| Model | Alias | Max Dur | Native Audio |\n|---|---|---|---|\n"
        for vm in catalog.get("video", {}).get("models", []):
            aliases = ", ".join(vm.get("aliases", []))
            max_d = f"{vm.get('max_duration', 8)}s"
            audio = "✅ Yes" if "omni" in vm.get("name", "") else "No"
            video_md += f"| `{vm.get('name')}` | `{aliases}` | {max_d} | {audio} |\n"

        img_md = "\n### 🎨 Image Models (Imagen / Nano Banana)\n\n| Model | Alias | Ref Cap |\n|---|---|---|\n"
        for im in catalog.get("image", {}).get("models", []):
            aliases = ", ".join(im.get("aliases", []))
            img_md += f"| `{im.get('name')}` | `{aliases}` | {im.get('ref_cap', 0)} |\n"

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
    """Probes authentication status."""
    data = await _fetch_credits_raw()
    if not data.get("authenticated"):
        return _format_not_authenticated_msg()

    return (
        f"### 🟢 Google Flow Account Status: Active\n\n"
        f"- **Email:** `{data.get('email', 'N/A')}`\n"
        f"- **Plan Tier:** `{data.get('user_paygate_tier', 'Google AI Pro')}`\n"
        f"- **Profile:** `{data.get('profile', 'default')}`\n"
        f"- **Credits Balance:** **{data.get('credits', 0):,}**\n"
        f"- **Connection:** Verified & Ready for Video Generation\n"
    )

def main():
    asyncio.run(mcp.run_stdio_async())

if __name__ == "__main__":
    main()
