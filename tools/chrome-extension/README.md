# Workforce Studio & Task Assistant (Chrome Extension)

A lightweight Manifest V3 Chrome extension connecting browser-based research, Google "Ask Gemini", Google Flow video generation, and Stitch prototypes directly with Workforce Studio Command Canvas (`http://127.0.0.1:8765`).

## Features

- **Ask Gemini & Google Flow Prompt Builder (Outbound)**: Select any active task from your workspace and copy prompts optimized for web research, sales outreach, Google Flow video generation, or Stitch UI design reviews.
- **Quick Capture (Inbound)**: Push research snippets, highlighted text, and webpage links into `workforces/inbox/pending/` via `POST /api/inbox/submit`.
- **Auto-Dispatch Routing**: Automatically convert incoming research items into active tasks or route them for human review via the canvas heartbeat watcher.
- **Context Menus**: Right-click any selected text to push it straight to Workforce Studio or capture prototype URLs with one click.
- **Real-Time Heartbeat Telemetry**: Live status badge indicating backend server state and process ID.

## How to Install (Unpacked)

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle in the top-right corner.
3. Click **Load unpacked**.
4. Select the `tools/chrome-extension/` directory from this repository.
5. Pin the extension icon to your toolbar.
