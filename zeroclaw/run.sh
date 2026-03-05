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

configure_ha_api_permissions() {
    HA_API_ALLOW_COVER=""
    HA_API_ALLOW_SCRIPT=""

    if jq -e '.allow_cover == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_COVER=1
    fi

    if jq -e '.allow_script == true' /data/options.json >/dev/null 2>&1; then
        HA_API_ALLOW_SCRIPT=1
    fi

    export HA_API_ALLOW_COVER
    export HA_API_ALLOW_SCRIPT
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
        seed_workspace
    fi

    ensure_skill
    generate_config
    telegram_health_check
    exec zeroclaw daemon
fi

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

generate_config
exec zeroclaw daemon
