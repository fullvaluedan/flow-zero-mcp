# 🎬 FlowZero MCP

> **Zero-cost Google Veo AI Video Generation, Live Credit Tracking & Full Creative Control for Claude, Cursor, and Agents.**  
> Powered by Google Flow (`flow.google.com`) and your active Google AI Pro / Ultra subscription.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Standard](https://img.shields.io/badge/MCP-Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Google Veo 3.1](https://img.shields.io/badge/Model-Google%20Veo%203.1-blue.svg)](https://deepmind.google/technologies/veo/)

---

## 💡 Why FlowZero?

Google's flagship video model **Veo** is available to Google AI Pro / Ultra subscribers via **Google Flow** (`flow.google.com`), but Google provides **no official public REST developer API** for Flow. If you try to use Google Cloud Vertex AI, you face metered developer pricing, credit card billing, and complex GCP setups.

**FlowZero MCP connects Claude Desktop, Claude Code, Cursor, and autonomous agents directly to Google Flow**:

- **$0 Extra API Billing** — Consumes your existing monthly subscription credit pool.
- **Live Credit Feed** — Shows your balance before generation, credits deducted, and live balance remaining on every output.
- **Full Google Flow Parity** — Vertical (`9:16` Shorts/Reels/TikTok) vs Horizontal (`16:9` Cinematic), 4s/6s/8s/10s durations, Veo Fast / Quality / Lite, and Omni Flash (with native audio).
- **Text-to-Video & Image-to-Video** — Animate initial image stills or interpolate start & end frames.
- **Clip Extension** — Extend existing clips by +8 seconds carrying audio and motion forward.

---

## 🛠️ Tools Included

| Tool | Description |
|---|---|
| `flow_generate_video` | Generates cinematic AI video via Veo 3.1 / Omni Flash. Supports 9:16 / 16:9, 4s/6s/8s/10s, T2V and I2V. Automatically feeds live credit status. |
| `flow_get_credits` | Standalone query for current credit balance, monthly subscription pool, and account tier. |
| `flow_extend_video` | Extends an existing video clip by another 8 seconds with continuous camera motion and audio. |
| `flow_generate_image` | High-res image generation via Imagen 3.5 & Nano Banana (`9:16`, `16:9`, `1:1`, `4:3`, `3:4`). |
| `flow_list_models` | Displays all available video and image models, aliases, max durations, and reference caps. |
| `flow_auth_status` | Probes session health and verifies the connected Google account. |

---

## 🚀 Quickstart & Setup

### 1. Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/fullvaluedan/flow-zero-mcp.git
cd flow-zero-mcp
pip install -e .
```

Ensure Playwright Chromium is available:
```bash
python -m playwright install chromium
```

---

### 2. One-Time Google Authentication

Before running generations in Claude, link your Google account (with Google AI Pro/Ultra subscription):

```bash
flow-zero-login
```
*(or run: `python -m flow_zero.auth`)*

1. A Chrome window will open to `flow.google.com`.
2. Sign into your Google Account.
3. FlowZero will securely save your local session cookies/tokens and verify your available credit balance.

---

### 3. Configure Claude Desktop

Add FlowZero to your `claude_desktop_config.json`:

* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "flow-zero": {
      "command": "flow-zero-mcp"
    }
  }
}
```

*Or run via Python directly:*
```json
{
  "mcpServers": {
    "flow-zero": {
      "command": "python",
      "args": ["-m", "flow_zero.server"]
    }
  }
}
```

> **Restart Claude Desktop** after updating your configuration.

---

## 💬 Example Prompts for Claude

Once connected, you can chat with Claude naturally:

### 1. Check Live Credits
> *"Claude, what is my Google Flow credit balance right now?"*

### 2. Vertical Short-Form Video (TikTok / Shorts / Reels)
> *"Generate a vertical 9:16 video of a barista crafting matcha latte art with delicate steam rising, cozy cafe lighting, 8 seconds long, using Veo Fast."*

### 3. Horizontal Cinematic Film Scene
> *"Generate a horizontal 16:9 cinematic shot of an ancient sandstone temple emerging from a swirling sandstorm at twilight, camera pulling backward, 8 seconds, using Veo Quality."*

### 4. Image-to-Video Animation
> *"Take this concept art image at `path/to/hero.png` and animate it: camera zooms in slightly, character blinks and smiles, vertical 9:16."*

### 5. Omni Flash with Native Audio (10 Seconds)
> *"Generate a 10-second video of rain falling on a tin roof in a lush tropical garden with ambient rain sounds using omni-flash."*

---

## 💳 Live Credit Tracker Sample Output

Whenever Claude generates a video, it automatically outputs a live credit card:

```markdown
### 🎬 Google Flow Video Generated Successfully!

#### 💳 Live Credit Tracker Feed
- **Account:** creator@gmail.com (Google AI Pro)
- **Balance Before:** 2,500 credits
- **Credits Deducted:** -20 credits
- **Live Balance Remaining:** 2,480 credits

#### 📹 Video Specifications
- **Prompt:** "Cyberpunk street in rain"
- **Orientation:** Vertical (9:16 - Shorts / Reels / TikTok)
- **Duration:** 8 seconds
- **Model:** veo-fast
- **Output File:** [cyberpunk_alley.mp4](file:///D:/Videos/Flow/cyberpunk_alley.mp4)
```

---

## 🔒 Security & Privacy

- All sessions and authentication cookies are stored **strictly locally** on your machine.
- No third-party servers, relays, or cloud brokers are used.
- Requests travel directly between your machine and Google's endpoints (`flow.google.com` / `aisandbox-pa.googleapis.com`).

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
