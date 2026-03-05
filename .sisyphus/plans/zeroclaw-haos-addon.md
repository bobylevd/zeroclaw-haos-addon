# ZeroClaw Home Assistant Add-on (Raspberry Pi Zero 2 W, Telegram Control)

## TL;DR
> **Summary**: Package ZeroClaw as a Home Assistant add-on (HAOS) and control it via Telegram; the add-on uses the Supervisor internal proxy + `SUPERVISOR_TOKEN` to discover entities/services and call HA services safely.
> **Deliverables**:
> - Home Assistant add-on repository (installable via URL)
> - Add-on container image (multi-arch: `armv7`, `aarch64`) with `zeroclaw` + `ha_api` helper
> - First-run bootstrap: write ZeroClaw config, snapshot HA entities/services into workspace, start `zeroclaw daemon`
> - A preloaded skill prompt (`skills/homeassistant/SKILL.md`) so the agent can operate HA safely
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: Add-on scaffold → runtime entrypoint/config generation → HA API helper + snapshot → Telegram wiring → build/publish → on-device QA

## Context
### Original Request
- “read about https://github.com/openagen/zeroclaw. i want to setup it on raspberry pi zero 2w, currently it has Home Asssistant os 17.3 (rpi 3), its main goal would be to manage home automation, so we need to predefine the agent stuff so that on the first run after user connects to it it would setup keys pickup existing home stuff and start working”

### Interview Summary
- Interaction surface: Telegram chat (selected).

### Metis Review (gaps addressed)
- Treat onboarding as non-interactive (HA add-ons cannot rely on TTY prompts).
- Avoid ZeroClaw `http_request` for Home Assistant because it blocks private / `.local` by design; use a narrow local helper command instead.
- Explicitly choose multi-arch (`armv7` + `aarch64`) for Pi Zero 2 W ambiguity.
- Guardrails: strict allowlists for HA service calls; deny “dangerous” domains by default; no HA config edits.
- Secrets: add-on options are masked in UI but stored plaintext in `/data/options.json`; document risk and provide redaction.

## Work Objectives
### Core Objective
- Provide a Home Assistant add-on that runs ZeroClaw on HAOS and can safely control the existing Home Assistant instance via Telegram, with automatic first-run discovery and minimal user steps.

### Deliverables
- A Home Assistant add-on repository containing one add-on: `zeroclaw`.
- A multi-arch image published to GHCR for `armv7` and `aarch64`.
- Add-on options/schema to configure:
  - LLM provider (`openrouter` default) + API key
  - Default model (optional override)
  - Telegram bot token
  - Optional Telegram allowlist (`*` default for first-run convenience)
  - Optional “expanded control” toggles (off by default)
- A constrained HA API helper command `ha_api` (no arbitrary URLs; no arbitrary services).
- A seeded workspace snapshot:
  - `homeassistant/states.json`
  - `homeassistant/services.json`
  - `homeassistant/inventory.md`
- A preloaded skills prompt at `skills/homeassistant/SKILL.md`.

### Definition of Done (verifiable)
- Repository can be added to Home Assistant as an add-on repository and the add-on installs.
- Add-on starts on HAOS with `homeassistant_api: true` and can successfully:
  - `GET http://supervisor/core/api/config` using `SUPERVISOR_TOKEN`
  - snapshot HA states/services into the ZeroClaw workspace
  - start `zeroclaw daemon` and respond via Telegram
- Safety constraints are enforced:
  - ZeroClaw `autonomy.allowed_commands` includes only `ha_api` (and no general-purpose network tools)
  - `ha_api` refuses any request outside its endpoint + service allowlists

### Must Have
- No interactive prompts required inside the container.
- No HA config edits by default (no writing to `/config`, no automation creation).
- No public inbound ports required (Telegram polling).
- Secrets are never printed to logs.

### Must NOT Have
- No “generic local HTTP bypass” added to ZeroClaw `http_request` (keep SSRF protections intact).
- No default enablement of high-risk actuation (`lock.*`, `alarm_control_panel.*`, garage-door covers, HA restart/shutdown).
- No additional chat channels until Telegram path is stable.

## Verification Strategy
> ZERO HUMAN INTERVENTION where feasible: unit/integration tests run in CI + local container smoke checks; HAOS end-to-end verification is scripted but requires a real HA instance.
- Test decision: tests-after (new repo)
- Evidence artifacts:
  - `.sisyphus/evidence/task-04-ha-api-tests.txt`
  - `.sisyphus/evidence/task-06-workspace-seed.txt`
  - `.sisyphus/evidence/task-09-ci-build.txt`
  - `.sisyphus/evidence/task-12-haos-e2e.txt`

## Execution Strategy
### Parallel Execution Waves
Wave 1 (Repo + Packaging Foundation)
Wave 2 (HA API Helper + Workspace Seeding)
Wave 3 (ZeroClaw Config + Telegram + Docs + QA)

### Dependency Matrix (full, all tasks)
- 1 blocks 2-12
- 2 blocks 3, 9
- 3 blocks 6-8, 12
- 4 blocks 5-8, 12
- 5 blocks 6-8, 12
- 9 blocks 10-12

### Agent Dispatch Summary
- Wave 1: 3 tasks (unspecified-high)
- Wave 2: 3 tasks (unspecified-high)
- Wave 3: 6 tasks (writing + unspecified-high)

## TODOs

- [x] 1. Create Home Assistant Add-on Repository Scaffold

  **What to do**:
  - Create a new repo (e.g. `zeroclaw-homeassistant-addon`) following Home Assistant “apps/add-ons” conventions.
  - Add `repository.yaml` at repo root.
  - Add add-on directory `zeroclaw/` with required metadata files: `config.yaml`, `build.yaml`, `Dockerfile`, `DOCS.md`, `README.md`, `CHANGELOG.md`.
  - Set add-on `arch` to `armv7` and `aarch64` (optionally include `armhf` only if explicitly tested).

  **Must NOT do**:
  - Do not include any secrets in repo.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: multi-file scaffold + CI config.
  - Skills: []

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2-12 | Blocked By: none

  **References**:
  - Pattern: https://raw.githubusercontent.com/home-assistant/addons-example/main/repository.yaml — repository metadata format
  - Pattern: https://raw.githubusercontent.com/home-assistant/addons-example/main/example/config.yaml — add-on `config.yaml` keys (options/schema/image)
  - Doc: https://developers.home-assistant.io/docs/apps/configuration — add-on/app structure and `/data/options.json`

  **Acceptance Criteria**:
  - [ ] Repo contains `repository.yaml` and add-on dir `zeroclaw/` with required files.

  **QA Scenarios**:
  ```
  Scenario: Repository structure sanity
    Tool: Bash
    Steps: ls -la; ls -la zeroclaw/
    Expected: required files present
    Evidence: .sisyphus/evidence/task-01-scaffold.txt

  Scenario: Minimal required keys present
    Tool: Bash
    Steps: |
      grep -q "^name:" repository.yaml && \
      grep -q "^url:" repository.yaml && \
      grep -q "^maintainer:" repository.yaml && \
      grep -q "^name:" zeroclaw/config.yaml && \
      grep -q "^slug:" zeroclaw/config.yaml && \
      grep -q "^arch:" zeroclaw/config.yaml
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-01-required-keys.txt
  ```

  **Commit**: YES | Message: `chore(addon): scaffold Home Assistant add-on repo` | Files: `repository.yaml`, `zeroclaw/*`

- [x] 2. Implement Add-on Options/Schema (Keys, Provider, Telegram)

  **What to do**:
  - In `zeroclaw/config.yaml`, define `options` + `schema` for:
    - `provider` (default: `openrouter`)
    - `api_key` (schema type: `password`)
    - `model` (optional string)
    - `telegram_bot_token` (schema type: `password`)
    - `telegram_allowed_users` (list of strings; default: `["*"]` for first-run)
    - `autonomy_level` (enum string; default: `supervised`)
    - `allow_cover` (bool; default false)
    - `allow_script` (bool; default false)
  - Set `homeassistant_api: true` so `SUPERVISOR_TOKEN` is available and the supervisor proxy works.

  Use Home Assistant add-on schema conventions (examples from official add-ons):
  - Optional values: set `options.<key>: null` and keep `schema.<key>` non-optional.
  - Lists: define schema as a YAML list of item types.

  Concrete target shape:
  ```yaml
  options:
    provider: openrouter
    api_key: null
    model: null
    telegram_bot_token: null
    telegram_allowed_users:
      - "*"
    autonomy_level: supervised
    allow_cover: false
    allow_script: false

  schema:
    provider: str
    api_key: password
    model: str?
    telegram_bot_token: password
    telegram_allowed_users:
      - str
    autonomy_level: list(read_only|supervised|full)
    allow_cover: bool
    allow_script: bool
  ```

  **Must NOT do**:
  - Do not attempt interactive prompts inside the container.
  - Do not default to `full` autonomy.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: config contract + security implications.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 3-8 | Blocked By: 1

  **References**:
  - Doc: https://developers.home-assistant.io/docs/apps/communication/ — `SUPERVISOR_TOKEN`, `homeassistant_api: true`, supervisor proxy URL
  - Pattern: https://raw.githubusercontent.com/home-assistant/addons/master/samba/config.yaml — schema types (`password`, list items)

  **Acceptance Criteria**:
  - [ ] `zeroclaw/config.yaml` includes `options` and `schema` for all required fields.

  **QA Scenarios**:
  ```
  Scenario: Options and schema sections exist
    Tool: Bash
    Steps: grep -q "^options:" zeroclaw/config.yaml && grep -q "^schema:" zeroclaw/config.yaml
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-02-options-schema.txt

  Scenario: Sensitive fields are password-typed in schema
    Tool: Bash
    Steps: |
      grep -q "^  api_key: password" zeroclaw/config.yaml && \
      grep -q "^  telegram_bot_token: password" zeroclaw/config.yaml
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-02-password-schema.txt
  ```

  **Commit**: YES | Message: `feat(addon): add options schema for provider and Telegram` | Files: `zeroclaw/config.yaml`

- [x] 3. Build Runtime Image (Debian) + Download ZeroClaw Binary

  **What to do**:
  - Implement `zeroclaw/Dockerfile` that:
    - starts with the Supervisor-provided build arg pattern:
      - `ARG BUILD_FROM`
      - `FROM $BUILD_FROM`
    - installs runtime deps: `ca-certificates`, `curl`, `tar`, `python3` (and `jq` if used in entrypoint)
    - downloads the latest ZeroClaw release binary for the container arch using the same target mapping as upstream bootstrap:
      - `aarch64-unknown-linux-gnu`
      - `armv7-unknown-linux-gnueabihf`
    - extracts and installs `zeroclaw` to `/usr/local/bin/zeroclaw`
    - adds `ha_api` helper and `run.sh` entrypoint
  - Prefer downloading from `zeroclaw-labs/zeroclaw` release assets (not the `openagen` fork, which may have no releases).

  **Must NOT do**:
  - Do not compile ZeroClaw on-device (HAOS). Compilation belongs in CI/build pipeline.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: multi-arch + supply-chain/security details.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 9-12 | Blocked By: 1

  **References**:
  - Upstream mapping logic: https://raw.githubusercontent.com/openagen/zeroclaw/main/scripts/bootstrap.sh (functions `detect_release_target` + `install_prebuilt_binary`)
  - Upstream download endpoint pattern: `https://github.com/zeroclaw-labs/zeroclaw/releases/latest/download/zeroclaw-${target}.tar.gz`
  - HA add-on Dockerfile pattern: https://raw.githubusercontent.com/home-assistant/addons-example/main/example/Dockerfile
  - HA build.yaml base pattern: https://raw.githubusercontent.com/home-assistant/addons-example/main/example/build.yaml

  **Acceptance Criteria**:
  - [ ] `docker build` succeeds for at least one arch locally (native arch).
  - [ ] Container can run `zeroclaw --help`.

  **QA Scenarios**:
  ```
  Scenario: Build image (native arch)
    Tool: Bash
    Steps: docker build -t zeroclaw-addon:dev zeroclaw/
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-03-docker-build.txt

  Scenario: ZeroClaw binary present
    Tool: Bash
    Steps: docker run --rm zeroclaw-addon:dev zeroclaw --help
    Expected: prints help and exits 0
    Evidence: .sisyphus/evidence/task-03-zeroclaw-help.txt
  ```

  **Commit**: YES | Message: `feat(addon): build image and bundle zeroclaw binary` | Files: `zeroclaw/Dockerfile`, `zeroclaw/build.yaml`

- [x] 4. Implement `ha_api` Helper (Constrained HA Core API Client)

  **What to do**:
  - Create an executable helper (recommended: single-file Python script) installed as `/usr/local/bin/ha_api`.
  - Default base URL: `http://supervisor/core/api`.
  - Auth header: `Authorization: Bearer ${SUPERVISOR_TOKEN}`.
  - Supported commands:
    - `ha_api health` (calls `/config` and returns OK/FAIL)
    - `ha_api list-states` (calls `/states`)
    - `ha_api list-services` (calls `/services`)
    - `ha_api get-state <entity_id>`
    - `ha_api call-service <domain> <service> --json <payload>`
  - Enforce allowlists:
    - Endpoint allowlist: only the above.
    - Service allowlist: safe defaults (lights/switches/scenes/fans/climate/media_player) with optional toggles for `cover` and `script`.
    - Deny-by-default for `lock`, `alarm_control_panel`, and any service containing `restart`, `shutdown`, `reboot`.
  - Add timeouts and max response size.
  - Ensure logs/errors never include the bearer token.

  **Must NOT do**:
  - No arbitrary URL fetch.
  - No free-form passthrough of `domain/service` without allowlist.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: safety-critical actuation boundary.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 5-8, 12 | Blocked By: 2, 3

  **References**:
  - HA add-on HA Core proxy + token: https://developers.home-assistant.io/docs/apps/communication/

  **Acceptance Criteria**:
  - [ ] `ha_api` rejects disallowed endpoints/services with non-zero exit.
  - [ ] `ha_api` supports overriding base URL for tests via env `HA_BASE_URL` only when `HA_API_ALLOW_TEST_BASE_URL=1`.

  **QA Scenarios**:
  ```
  Scenario: Disallowed service is blocked
    Tool: Bash
    Steps: docker run --rm zeroclaw-addon:dev ha_api call-service lock lock --json '{"entity_id":"lock.front_door"}'
    Expected: exit non-zero; error mentions disallowed domain/service
    Evidence: .sisyphus/evidence/task-04-block-lock.txt

  Scenario: Disallowed URL override is blocked by default
    Tool: Bash
    Steps: docker run --rm -e HA_BASE_URL=http://example.com zeroclaw-addon:dev ha_api health
    Expected: exit non-zero; error mentions test override disabled
    Evidence: .sisyphus/evidence/task-04-block-url.txt
  ```

  **Commit**: YES | Message: `feat(addon): add constrained ha_api helper` | Files: `zeroclaw/ha_api` (or equivalent)

- [x] 5. Add Workspace Seeding (States/Services Snapshot + Inventory Markdown)

  **What to do**:
  - Implement a seeding step run on container start when no snapshot exists (or when snapshot is older than N hours):
    - `ha_api list-states` → write to `$ZEROCLAW_WORKSPACE/homeassistant/states.json`
    - `ha_api list-services` → write to `$ZEROCLAW_WORKSPACE/homeassistant/services.json`
    - Generate `$ZEROCLAW_WORKSPACE/homeassistant/inventory.md` summarizing:
      - counts by domain
      - a table of “friendly_name → entity_id” for common domains
  - Keep snapshot size bounded (truncate huge attribute blobs).

  **Must NOT do**:
  - Do not store bearer tokens or secrets in workspace.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: affects first-run UX and reliability.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 6-8, 12 | Blocked By: 4

  **References**:
  - ZeroClaw workspace/skills location: https://raw.githubusercontent.com/openagen/zeroclaw/main/src/skills/mod.rs (workspace `skills/` convention)

  **Acceptance Criteria**:
  - [ ] On startup with valid Supervisor token, snapshot files are created under workspace.

  **QA Scenarios**:
  ```
  Scenario: Seed step is idempotent
    Tool: Bash
    Steps: docker run --rm -e SUPERVISOR_TOKEN=fake -e ZEROCLAW_WORKSPACE=/tmp/ws zeroclaw-addon:dev /run.sh --seed-only || true
    Expected: exits non-zero with clear HA connectivity error (no token/HA), but does not crash; produces no secret output
    Evidence: .sisyphus/evidence/task-05-seed-idempotent.txt
  ```

  **Commit**: YES | Message: `feat(addon): seed HA inventory into workspace` | Files: entrypoint + seeding scripts

- [x] 6. Generate ZeroClaw `config.toml` from Add-on Options

  **What to do**:
  - Implement container entrypoint (`run.sh` or s6 service) to:
    - read `/data/options.json`
    - write `/data/.zeroclaw/config.toml` with:
      - `default_provider`, `default_model`, `api_key`
      - `[channels_config.telegram]` with `bot_token` and `allowed_users`
      - `[autonomy]` set to supervised; `allowed_commands = ["ha_api"]`
      - disable `http_request` and `browser`
      - set `workspace_dir` to `/data/workspace`
      - set `[secrets].encrypt = true`
      - set `[memory].backend = "sqlite"` (default) and keep the sqlite DB under `/data/.zeroclaw/` or `/data/workspace/`
    - set env: `HOME=/data`, `ZEROCLAW_WORKSPACE=/data/workspace`
  - Start `zeroclaw daemon` in foreground.

  Add non-production helper flags used by QA (must not leak secrets):
  - `--print-config`: render the generated config with secrets redacted
  - `--seed-only`: run HA snapshot step then exit
  - `--ensure-skill`: copy the skill template into workspace then exit

  **Must NOT do**:
  - Do not echo options.json contents to logs.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: config contract + secret handling.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 7, 12 | Blocked By: 2, 3, 4, 5

  **References**:
  - ZeroClaw config contract: https://raw.githubusercontent.com/openagen/zeroclaw/main/docs/config-reference.md
  - ZeroClaw channels keys: https://raw.githubusercontent.com/openagen/zeroclaw/main/docs/channels-reference.md

  **Acceptance Criteria**:
  - [ ] With a synthetic `options.json`, container generates `/data/.zeroclaw/config.toml` and starts `zeroclaw daemon`.

  **QA Scenarios**:
  ```
  Scenario: Config file generation
    Tool: Bash
    Steps: |
      tmp=$(mktemp -d) && \
      printf '%s' '{"provider":"openrouter","api_key":"x","telegram_bot_token":"y","telegram_allowed_users":["*"],"autonomy_level":"supervised"}' > "$tmp/options.json" && \
      docker run --rm -v "$tmp:/data" zeroclaw-addon:dev /run.sh --print-config
    Expected: printed config does not include raw keys; shows expected provider/model and telegram enabled
    Evidence: .sisyphus/evidence/task-06-config-gen.txt
  ```

  **Commit**: YES | Message: `feat(addon): generate zeroclaw config and start daemon` | Files: `zeroclaw/run.sh` (or equivalent)

- [x] 7. Add Preloaded Skill Prompt for Home Automation

  **What to do**:
  - Add `skills/homeassistant/SKILL.md` into the workspace on first run (copy from image into `/data/workspace/skills/homeassistant/SKILL.md`).
  - Skill content must instruct the agent to:
    - always call `ha_api list-states` (or read snapshot) before acting
    - map user-friendly names to `entity_id`
    - never operate on forbidden domains
    - prefer existing scenes/scripts where possible
    - ask clarification if multiple candidate entities match

  **Must NOT do**:
  - Do not encourage the agent to run arbitrary shell commands.

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: prompt engineering + safety policy.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 6

  **References**:
  - Skills path convention: https://raw.githubusercontent.com/openagen/zeroclaw/main/src/skills/mod.rs

  **Acceptance Criteria**:
  - [ ] Skill file is present under `/data/workspace/skills/homeassistant/SKILL.md` after first start.

  **QA Scenarios**:
  ```
  Scenario: Skill file presence
    Tool: Bash
    Steps: docker run --rm zeroclaw-addon:dev /run.sh --ensure-skill && test -f /data/workspace/skills/homeassistant/SKILL.md
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-07-skill-present.txt
  ```

  **Commit**: YES | Message: `feat(skill): add Home Assistant operating guidelines` | Files: skill template files

- [x] 8. Add Startup Health Checks + Clear “Not Configured” Mode

  **What to do**:
  - In entrypoint, if required options are missing, exit non-zero with a clear single-line error pointing to add-on config UI.
  - If HA API is unreachable, log clear diagnostics (without secrets) and exit non-zero.
  - If Telegram token is invalid, fail fast (or at least bubble a clear error from `zeroclaw channel doctor`).

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: reliability + operator UX.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 6

  **References**:
  - HA proxy test example (curl): https://developers.home-assistant.io/docs/apps/communication/

  **Acceptance Criteria**:
  - [ ] Missing keys => deterministic exit with actionable message.
  - [ ] HA unreachable => deterministic exit with actionable message.

  **QA Scenarios**:
  ```
  Scenario: Missing API key fails clearly
    Tool: Bash
    Steps: docker run --rm zeroclaw-addon:dev /run.sh
    Expected: exit non-zero; stderr contains "api_key" and "add-on configuration"
    Evidence: .sisyphus/evidence/task-08-missing-key.txt
  ```

  **Commit**: YES | Message: `fix(addon): fail fast with clear configuration errors` | Files: entrypoint

- [x] 9. Add CI Build/Publish to GHCR (Multi-Arch)

  **What to do**:
  - Add GitHub Actions workflow based on `home-assistant/addons-example` builder workflow.
  - Build/publish `armv7` and `aarch64` images on push to `main`.
  - Set the add-on `image:` key to point to `ghcr.io/<owner>/{arch}-addon-zeroclaw` (or chosen naming).

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: CI + registry permissions.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 10-12 | Blocked By: 1, 3

  **References**:
  - Workflow pattern: https://raw.githubusercontent.com/home-assistant/addons-example/main/.github/workflows/builder.yaml

  **Acceptance Criteria**:
  - [ ] CI runs on PR (test build) and on main (publish).

  **QA Scenarios**:
  ```
  Scenario: Workflow YAML sanity
    Tool: Bash
    Steps: python -c "import yaml; yaml.safe_load(open('.github/workflows/builder.yaml'))"
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-09-workflow-parse.txt
  ```

  **Commit**: YES | Message: `ci(addon): build and publish multi-arch images` | Files: `.github/workflows/builder.yaml`

- [x] 10. Write Operator Docs (Install + First Run + Security)

  **What to do**:
  - In `zeroclaw/DOCS.md`, document:
    - adding repo URL in HA
    - configuring provider key and telegram token
    - how to tighten Telegram allowlist after first run
    - explicit warning: options are stored in `/data/options.json` (masked UI, not encrypted)
    - how to view logs and run diagnostics (`zeroclaw status`, `zeroclaw doctor`, `zeroclaw channel doctor`)
  - Add a short troubleshooting section (no HA access, telegram no replies, etc.).

  **Recommended Agent Profile**:
  - Category: `writing` — Reason: user-facing runbook.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 9

  **References**:
  - ZeroClaw ops commands: https://raw.githubusercontent.com/openagen/zeroclaw/main/docs/operations-runbook.md
  - ZeroClaw channels troubleshooting: https://raw.githubusercontent.com/openagen/zeroclaw/main/docs/channels-reference.md
  - HA add-on communication model: https://developers.home-assistant.io/docs/apps/communication/

  **Acceptance Criteria**:
  - [ ] Docs include install, config, security warning, and troubleshooting.

  **QA Scenarios**:
  ```
  Scenario: Docs mention secrets storage risk
    Tool: Bash
    Steps: python -c "p=open('zeroclaw/DOCS.md').read().lower(); assert 'options.json' in p and 'plaintext' in p"
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-10-docs-risk.txt
  ```

  **Commit**: YES | Message: `docs(addon): installation and security notes` | Files: `zeroclaw/DOCS.md`, `zeroclaw/README.md`

- [x] 11. Add Local Smoke Test Harness (No HA Required)

  **What to do**:
  - Provide a minimal `scripts/smoke.sh` that:
    - builds the image
    - runs `zeroclaw --help`
    - runs entrypoint in “print-config” mode with a synthetic `/data/options.json`
    - runs `ha_api` in “self-check” mode that validates allowlist logic without talking to HA

  **Recommended Agent Profile**:
  - Category: `unspecified-low` — Reason: simple scripting.
  - Skills: []

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 12 | Blocked By: 3, 6

  **References**:
  - N/A

  **Acceptance Criteria**:
  - [ ] `scripts/smoke.sh` exits 0 on developer machine with Docker.

  **QA Scenarios**:
  ```
  Scenario: Smoke script runs
    Tool: Bash
    Steps: bash scripts/smoke.sh
    Expected: exit 0
    Evidence: .sisyphus/evidence/task-11-smoke.txt
  ```

  **Commit**: YES | Message: `test(addon): add local smoke harness` | Files: `scripts/smoke.sh`

- [ ] 12. HAOS End-to-End Verification (Telegram + HA Discovery)

  **What to do**:
  - Install add-on on HAOS 17.3.
  - Configure options (provider key + telegram token).
  - Start add-on; verify logs show:
    - HA proxy connectivity OK
    - snapshot created
    - `zeroclaw daemon` running
  - From Telegram, send a prompt like: “List my lights and turn on the kitchen light.”
  - Confirm the agent:
    - reads snapshot or queries states
    - calls HA service via `ha_api`
    - reports result

  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: real deployment QA.
  - Skills: []

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: none | Blocked By: 1-11

  **References**:
  - HA proxy example curl: https://developers.home-assistant.io/docs/apps/communication/

  **Acceptance Criteria**:
  - [ ] Telegram message results in HA service call for an allowed domain.
  - [ ] Forbidden service calls are rejected and explained.

  **QA Scenarios**:
  ```
  Scenario: HA API connectivity from add-on container
    Tool: Bash
    Steps: curl -sS -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" http://supervisor/core/api/config | jq -r '.version'
    Expected: prints a version string
    Evidence: .sisyphus/evidence/task-12-ha-config.txt

  Scenario: Forbidden domain refused
    Tool: Bash
    Steps: ha_api call-service lock unlock --json '{"entity_id":"lock.front_door"}'
    Expected: exit non-zero; clear error
    Evidence: .sisyphus/evidence/task-12-forbidden.txt
  ```

  **Commit**: NO | Message: N/A | Files: N/A

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [x] F1. Plan Compliance Audit — oracle
- [x] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high
- [x] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit 1: scaffold repo + add-on metadata
- Commit 2: Dockerfile/build + bundling zeroclaw binary
- Commit 3: ha_api helper + seeding
- Commit 4: entrypoint config generation + daemon start + health checks
- Commit 5: docs + smoke harness

## Success Criteria
- User can install the add-on from a repository URL on HAOS and control HA entities via Telegram within 10 minutes.
- No secrets appear in logs.
- Default behavior is safe-by-default with clear expansion toggles.
