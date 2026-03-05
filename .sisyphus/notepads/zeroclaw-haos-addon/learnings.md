# Learnings

- Home Assistant add-on repository scaffold requires root  with , , .
- Minimal add-on  should include , , , , , arm64, and ; keep / for later tasks.
- For this add-on, arm64 must explicitly include both  and .

- Home Assistant add-on repository scaffold requires root "repository.yaml" with keys "name", "url", and "maintainer".
- Minimal add-on "config.yaml" should include "name", "version", "slug", "description", "url", "arch", and "init: false"; keep "options" and "schema" for later tasks.
- For this add-on, "arch" must explicitly include both "armv7" and "aarch64".
- ZeroClaw release download should pin "v0.1.7"; latest release download endpoint is unreliable for ARM assets.
- Runtime image logic depends on HA/Builder-provided "BUILD_ARCH" mapping (armv7->armv7-unknown-linux-gnueabihf, aarch64->aarch64-unknown-linux-gnu) and "ZEROCLAW_VERSION" build arg for pinning.
- Runtime packages must include `python3` and `jq` for upcoming `ha_api` helper and options parsing needs.
- `ha_api` defaults to `http://supervisor/core/api` and requires `SUPERVISOR_TOKEN`; `HA_BASE_URL` is rejected unless `HA_API_ALLOW_TEST_BASE_URL=1` is set.
- `ha_api` service allowlist defaults to `light`, `switch`, `scene`, `fan`, `climate`, `media_player`; `cover` and `script` are opt-in via `HA_API_ALLOW_COVER=1` and `HA_API_ALLOW_SCRIPT=1`.
- `ha_api call-service` deny-by-default blocks `lock`, `alarm_control_panel`, and any domain/service containing `restart`, `shutdown`, or `reboot` (case-insensitive).

- Workspace seeding default max age is 24h (`ZEROCLAW_SNAPSHOT_MAX_AGE_HOURS` override) and freshness requires all three files: `states.json`, `services.json`, `inventory.md`.
- Seeding writes to `$ZEROCLAW_WORKSPACE/homeassistant/` (default `/data/workspace/homeassistant/`) and is wired into `/run.sh` for startup plus `--seed-only` mode.
- Snapshot truncation stores sanitized state records (`entity_id`, state timestamps, safe attribute allowlist) and compact service metadata (description + field names), dropping secret-like keys.
- ZeroClaw config generation maps add-on `autonomy_level: read_only` to TOML `[autonomy].level = "readonly"`; `supervised` and `full` pass through.
- Generated `config.toml` keys used by schema: top-level `default_provider`, optional `default_model`, `api_key`; `[channels_config] cli=false`; `[channels_config.telegram] bot_token, allowed_users`; `[autonomy] level, allowed_commands=["ha_api"]`; `[http_request].enabled=false`; `[browser].enabled=false`; `[secrets].encrypt=true`; `[memory].backend="sqlite"`.
- `--print-config` redaction masks `api_key` and `channels_config.telegram.bot_token` while preserving non-secret config for QA checks.
- HA skill template is embedded in the add-on image at `/opt/zeroclaw/skills/homeassistant/SKILL.md` for startup copy into workspace.
- Startup validation now fails config generation when required add-on keys (`api_key`, `telegram_bot_token`) are missing/blank, with a single-line `add-on configuration` error.
- Health checks run only on daemon-start: `ha_api health` runs only when `SUPERVISOR_TOKEN` is set, and `zeroclaw channel doctor` runs after config generation to fail fast on Telegram issues.
