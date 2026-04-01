# ZeroClaw Add-on

AI-powered home automation agent for Home Assistant, controlled via Telegram.

## Install

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**.
2. Open the three-dot menu and select **Repositories**.
3. Paste this repository URL and close the dialog.
4. Find **ZeroClaw** in the store and click **Install**.

## Configure

Go to the add-on **Configuration** tab and set:

### Required

| Option | Description |
|--------|-------------|
| `provider` | LLM provider. Default: `openrouter`. Also supports `openai` and others. |
| `api_key` | API key for your LLM provider. |
| `telegram_bot_token` | Telegram bot token from [@BotFather](https://t.me/BotFather). |

### Recommended

| Option | Default | Description |
|--------|---------|-------------|
| `model` | *(provider default)* | LLM model name. Required for OpenRouter (e.g., `anthropic/claude-sonnet-4`). Optional for OpenAI. |
| `telegram_allowed_users` | `["*"]` | List of Telegram user IDs (as strings) allowed to talk to the bot. Use `"*"` for first setup, then restrict. To find your ID, message [@userinfobot](https://t.me/userinfobot) on Telegram. |

### Autonomy

| Option | Default | Description |
|--------|---------|-------------|
| `autonomy_level` | `supervised` | `read_only` — agent can only query, never actuate. `supervised` — agent executes commands but asks for confirmation on ambiguous or risky actions. `full` — agent acts without confirmation (use with caution). |

### Safety Toggles

These are off by default. Enable only what you need.

| Option | Default | What it unlocks |
|--------|---------|-----------------|
| `allow_cover` | `false` | Control blinds, curtains, garage doors. |
| `allow_script` | `false` | Run Home Assistant scripts. |
| `allow_automation` | `false` | Create, edit, and delete HA automations. |
| `allow_event` | `false` | Fire custom events. |

Locks and alarm panels are always blocked regardless of these settings.

### Cost & Memory

| Option | Default | Description |
|--------|---------|-------------|
| `enable_memory` | `true` | Store user preferences across conversations. |
| `enable_cost_tracking` | `true` | Track LLM API usage costs. |
| `daily_cost_limit_usd` | `2.0` | Daily spending cap in USD. |
| `snapshot_refresh_hours` | `4` | How often to refresh the Home Assistant entity snapshot (hours). |

## First Run

1. Start the add-on from the **Info** tab.
2. Open the **Log** tab — wait for `ZeroClaw started. Found X areas, Y entities. Ready.`
3. Open Telegram and send your bot a message like **"What devices do I have?"**
4. The agent will read your home inventory and introduce itself. It will ask about:
   - Preferred device names (aliases)
   - Rooms or devices to avoid
   - Routines to set up (e.g., good morning, good night)
5. Answer the questions — preferences are stored and used in future conversations.

### What You Can Ask

- "Turn on the kitchen light"
- "Set bedroom to 22 degrees"
- "What's the living room temperature?"
- "Play music on the WiiM"
- "Add milk to the shopping list"
- "What happened in the last hour?"
- "Create a good night routine"

## Security Warning

Add-on options (including API keys and bot token) are stored as plaintext in `/data/options.json` on the host. Treat host access and backups as sensitive. Rotate keys if this file is exposed.

## Logs and Diagnostics

- **Add-on logs**: Settings > Add-ons > ZeroClaw > Log tab.
- **CLI diagnostics** (from add-on terminal):
  - `zeroclaw status` — daemon status
  - `zeroclaw doctor` — full health check
  - `zeroclaw channel doctor` — Telegram connectivity check

## Troubleshooting

### Add-on fails to start

- Check the Log tab for error messages.
- Verify `api_key` and `telegram_bot_token` are set (not null).
- If logs show "Home Assistant is unreachable", the HA supervisor may still be booting — the add-on retries 5 times with 5-second intervals. If it still fails, check supervisor connectivity.

### Bot doesn't respond to messages

- Verify `telegram_bot_token` is correct (test with `zeroclaw channel doctor`).
- Check that your Telegram user ID is in `telegram_allowed_users` (or set to `"*"`).
- Make sure no other bot or service is polling the same bot token.

### Agent controls the wrong device

- Say "list my devices" to see what the agent knows about.
- Tell it preferred names: "Call the living room WiiM 'speaker'" — it will remember.
- If entities are missing, say "refresh" to re-scan Home Assistant.

### Agent acts on stale data

- Entity snapshots refresh every `snapshot_refresh_hours` (default: 4h) and on every restart.
- Say "refresh" to force an immediate re-scan.
