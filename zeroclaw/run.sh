#!/bin/sh
set -eu

export HOME=/data
export ZEROCLAW_WORKSPACE=/data/workspace

CONFIG_DIR="${HOME}/.zeroclaw"
CONFIG_PATH="${CONFIG_DIR}/config.toml"
CONFIG_HELPER="/usr/local/bin/generate_config"
SKILL_TEMPLATE="/opt/zeroclaw/skills/homeassistant/SKILL.md"

seed_workspace() {
    /usr/local/bin/seed_workspace
}

generate_config() {
    "${CONFIG_HELPER}" --options /data/options.json --output "${CONFIG_PATH}"
}

print_config() {
    "${CONFIG_HELPER}" --options /data/options.json --output "${CONFIG_PATH}" --print-redacted
}

ensure_skill() {
    skill_target_dir="${ZEROCLAW_WORKSPACE}/skills/homeassistant"
    skill_target_file="${skill_target_dir}/SKILL.md"
    mkdir -p "${skill_target_dir}"
    if [ -f "${SKILL_TEMPLATE}" ]; then
        cp "${SKILL_TEMPLATE}" "${skill_target_file}"
        printf '%s\n' "Ensured Home Assistant skill at ${skill_target_file}"
    else
        printf '%s\n' "Home Assistant skill template not found at ${SKILL_TEMPLATE}" >&2
    fi
}

is_daemon_start() {
    [ "$#" -eq 0 ] || { [ "$#" -eq 1 ] && [ "${1:-}" = "zeroclaw" ]; }
}

ha_health_check() {
    if ! ha_api health >/dev/null 2>&1; then
        printf '%s\n' "ERROR: Home Assistant is unreachable; verify add-on configuration and Supervisor connectivity." >&2
        exit 1
    fi
}

telegram_health_check() {
    if ! zeroclaw channel doctor >/dev/null 2>&1; then
        printf '%s\n' "ERROR: Telegram health check failed; verify add-on configuration for telegram_bot_token." >&2
        exit 1
    fi
}

send_startup_greeting() {
    ONBOARDING_MARKER="${ZEROCLAW_WORKSPACE}/.onboarded"
    BOT_TOKEN=$(jq -r '.telegram_bot_token // empty' /data/options.json)
    ALLOWED=$(jq -r '.telegram_allowed_users[0] // empty' /data/options.json)

    if [ -z "${BOT_TOKEN}" ] || [ -z "${ALLOWED}" ] || [ "${ALLOWED}" = "*" ]; then
        return 0
    fi

    INVENTORY="${ZEROCLAW_WORKSPACE}/homeassistant/inventory.md"
    if [ -f "${INVENTORY}" ]; then
        ENTITY_COUNT=$(grep -c '^\|' "${INVENTORY}" 2>/dev/null || echo "0")
        AREA_COUNT=$(grep -c '^## ' "${INVENTORY}" 2>/dev/null || echo "0")
    else
        ENTITY_COUNT="0"
        AREA_COUNT="0"
    fi

    if [ -f "${ONBOARDING_MARKER}" ]; then
        MSG="🏠 ZeroClaw restarted. Found ${AREA_COUNT} areas, ${ENTITY_COUNT} entities. Ready."
    else
        MSG="👋 ZeroClaw is connected to your Home Assistant.

I found ${AREA_COUNT} areas and ${ENTITY_COUNT} entities.

Send me a message like:
• \"What devices do I have?\"
• \"Turn on the kitchen light\"
• \"Set bedroom to 22 degrees\"

I'll learn your preferences as we go. Say \"help\" anytime."
        touch "${ONBOARDING_MARKER}"
    fi

    TG_URL="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"
    PAYLOAD=$(printf '{"chat_id":%s,"text":"%s","parse_mode":"Markdown"}' \
        "${ALLOWED}" \
        "$(printf '%s' "${MSG}" | sed 's/"/\\"/g')")

    curl -sS -X POST "${TG_URL}" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" >/dev/null 2>&1 || true
}

configure_ha_api_permissions() {
    HA_API_ALLOW_COVER=""
    HA_API_ALLOW_SCRIPT=""
    HA_API_ALLOW_AUTOMATION=""
    HA_API_ALLOW_EVENT=""

    if jq -e '.allow_cover == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_COVER=1
    fi

    if jq -e '.allow_script == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_SCRIPT=1
    fi

    if jq -e '.allow_automation == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_AUTOMATION=1
    fi

    if jq -e '.allow_event == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_EVENT=1
    fi

    export HA_API_ALLOW_COVER
    export HA_API_ALLOW_SCRIPT
    export HA_API_ALLOW_AUTOMATION
    export HA_API_ALLOW_EVENT
}

snapshot_max_age_hours() {
    jq -r '.snapshot_refresh_hours // 4' /data/options.json
}

mkdir -p "${CONFIG_DIR}" "${ZEROCLAW_WORKSPACE}"

if [ "${1:-}" = "--print-config" ]; then
    print_config
    exit 0
fi

if [ "${1:-}" = "--ensure-skill" ]; then
    ensure_skill
    exit 0
fi

if [ "${1:-}" = "--seed-only" ]; then
    seed_workspace
    exit $?
fi

if is_daemon_start "$@"; then
    configure_ha_api_permissions

    if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
        ha_health_check
        seed_workspace --max-age-hours "$(snapshot_max_age_hours)"
    fi

    ensure_skill
    generate_config
    chmod 600 "${CONFIG_PATH}"
    send_startup_greeting
    exec zeroclaw daemon
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

generate_config
exec zeroclaw daemon
