# README - What You Need To Do (HAOS E2E + Manual QA)

This repo is ready for the last two plan items that require a real Home Assistant OS device and your real Telegram bot.

Remaining unchecked items in `.sisyphus/plans/zeroclaw-haos-addon.md`:
- 12. HAOS End-to-End Verification (Telegram + HA Discovery)
- F3. Real Manual QA

## Prereqs
- A running Home Assistant OS 17.3 instance (Pi Zero 2 W target is fine).
- A Telegram bot token (from BotFather).
- Your Telegram user ID(s) (numeric). If you don't know it, message a bot like `@userinfobot`.
- An LLM provider API key (per your chosen provider).

## 1) Add the repository in Home Assistant
1. Home Assistant -> Settings -> Add-ons -> Add-on Store.
2. 3-dot menu -> Repositories.
3. Add:
   - `https://github.com/dbobylev/zeroclaw-haos-addon`
4. Close dialog, refresh store.

## 2) Install and configure the add-on
1. Find **ZeroClaw** add-on -> Install.
2. Open **Configuration** and set these options (names must match exactly):
   - `provider`: e.g. `openrouter` (or whatever you're using)
   - `api_key`: your provider API key
   - `model`: optional (leave blank/null if not needed)
   - `telegram_bot_token`: your Telegram bot token
   - `telegram_allowed_users`: start strict, e.g. `["123456789"]` (use `"*"` only for a quick debug run)
   - `autonomy_level`: `read_only` | `supervised` | `full`
   - `allow_cover`: `false` unless you explicitly need covers
   - `allow_script`: `false` unless you explicitly need scripts
3. Save.

## 3) Start the add-on and check logs
1. Start the add-on.
2. Open Logs.
3. Expected high-level behavior:
   - If `SUPERVISOR_TOKEN` is present: HA health check runs, workspace seed tries to run.
   - Skill file is ensured at `/data/workspace/skills/homeassistant/SKILL.md`.
   - Config generated at `/data/.zeroclaw/config.toml`.
   - `zeroclaw channel doctor` runs to validate Telegram config.
   - `zeroclaw daemon` runs in foreground.

If startup fails, copy/paste the first error line + ~30 lines around it.

## 4) Capture required evidence (paste back here)

Fill these files (they already exist):
- `.sisyphus/evidence/task-12-ha-config.txt`
- `.sisyphus/evidence/task-12-forbidden.txt`

Commands to run:

1) HA proxy connectivity (inside add-on container, or HAOS shell that has token):
```
curl -sS -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" http://supervisor/core/api/config | jq -r '.version'
```

2) Forbidden domain must be blocked (inside add-on container):
```
ha_api call-service lock unlock --json '{"entity_id":"lock.front_door"}'
```
Expected: non-zero exit with a clear error.

## 5) Telegram end-to-end prompt test
From an allowed Telegram user, send:
- "List my lights and turn on the kitchen light."

Expected:
- Agent reads snapshot (or queries states/services) and uses `ha_api` to act.
- Response clearly states which entity_id + service was called.

Also send a blocked request:
- "Unlock the front door"

Expected:
- Refusal with explanation (locks are blocked).

## What to paste back to finish Task 12 + F3
1) Add-on logs from startup (copy/paste).
2) Output of the HA version curl command.
3) Exit code + error line from the forbidden-domain command.
4) Telegram chat transcript snippet showing one allowed action + one blocked action.
