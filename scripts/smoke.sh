#!/usr/bin/env bash
set -eu

IMAGE_TAG="zeroclaw-addon:dev"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

cat >"${TMP_DIR}/options.json" <<'EOF'
{
  "provider": "openai",
  "api_key": "smoke-test-api-key",
  "model": "gpt-4o-mini",
  "telegram_bot_token": "123456:smoke-test-bot-token",
  "telegram_allowed_users": ["*"],
  "autonomy_level": "supervised",
  "allow_cover": true,
  "allow_script": false
}
EOF

docker build -t "${IMAGE_TAG}" zeroclaw/ >/dev/null 2>&1
docker run --rm "${IMAGE_TAG}" zeroclaw --help >/dev/null 2>&1

PRINT_CONFIG_OUTPUT="$(docker run --rm -v "${TMP_DIR}/options.json:/data/options.json:ro" "${IMAGE_TAG}" --print-config)"

case "${PRINT_CONFIG_OUTPUT}" in
  *"***REDACTED***"*) ;;
  *)
    printf '%s\n' "ERROR: redacted marker missing from --print-config output" >&2
    exit 1
    ;;
esac

case "${PRINT_CONFIG_OUTPUT}" in
  *"smoke-test-api-key"*|*"smoke-test-bot-token"*)
    printf '%s\n' "ERROR: raw secrets leaked in --print-config output" >&2
    exit 1
    ;;
  *) ;;
esac

if docker run --rm "${IMAGE_TAG}" ha_api call-service lock lock --json '{"entity_id":"lock.front_door"}' >/dev/null 2>&1; then
  printf '%s\n' "ERROR: disallowed lock service call unexpectedly succeeded" >&2
  exit 1
fi

if docker run --rm -e HA_BASE_URL=http://example.com "${IMAGE_TAG}" ha_api health >/dev/null 2>&1; then
  printf '%s\n' "ERROR: HA_BASE_URL override unexpectedly succeeded" >&2
  exit 1
fi

printf '%s\n' "OK"
