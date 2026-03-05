# ZeroClaw Add-on

Operator guide for the Home Assistant OS add-on.

## Install

1. In Home Assistant, open **Settings -> Add-ons -> Add-on Store**.
2. Open the three-dot menu, select **Repositories**.
3. Add this repository URL, then close the dialog.
4. Find **ZeroClaw** in the store and install it.

## Configure

Set the add-on options before first start:

- `provider`, `api_key`, `model`
- `telegram_bot_token`
- `telegram_allowed_users`
- Optional capability flags: `allow_cover`, `allow_script`

`telegram_allowed_users` is a Telegram sender allowlist (user IDs as strings) or `"*"` to allow any sender.

Home Assistant actuation is controlled by `ha_api` service allowlists. Keep service allowlists minimal; set `allow_cover` and `allow_script` only when you explicitly need those capabilities.

## First Run

1. Start the add-on.
2. Open add-on logs and wait for startup to complete.
3. Send a Telegram message to the bot to verify replies.
4. Confirm expected Home Assistant entities are reachable.

Runtime behavior and generated files:

- Telegram integration uses polling only (no inbound ports required).
- Generated runtime config: `/data/.zeroclaw/config.toml`
- Workspace root: `/data/workspace/`
- Home Assistant snapshots: `/data/workspace/homeassistant/*`
- Home Assistant skill file: `/data/workspace/skills/homeassistant/SKILL.md`

After first run, tighten `telegram_allowed_users` and `ha_api` service allowlists to only what you need.

## Security Warning

Home Assistant masks secret fields in the UI, but add-on options are still stored as `plaintext` on disk in `/data/options.json`.

- Treat host access and backups as sensitive.
- Rotate keys and tokens if this file is exposed.

## Logs and Diagnostics

- Add-on runtime logs: Home Assistant UI -> **Settings -> Add-ons -> ZeroClaw -> Logs**
- CLI diagnostics inside the add-on:
  - `zeroclaw status`
  - `zeroclaw doctor`
  - `zeroclaw channel doctor`

## Troubleshooting

### Home Assistant is unreachable

- Check Supervisor token availability in add-on environment/options.
- Verify Home Assistant Supervisor proxy/API connectivity from inside the add-on.
- Run `zeroclaw doctor` and review reported API/proxy failures.

### Telegram bot does not reply

- Verify `telegram_bot_token` is correct.
- Confirm your Telegram sender ID is allowed by `telegram_allowed_users`.
- Run `zeroclaw channel doctor` to validate Telegram channel health.
