#!/usr/bin/python3

import json
import sys
from collections.abc import Sequence
from pathlib import Path


def parse_args(argv: Sequence[str]) -> tuple[Path, Path, bool]:
    options_path: Path | None = None
    output_path: Path | None = None
    print_redacted = False

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--print-redacted":
            print_redacted = True
            index += 1
            continue

        if arg in {"--options", "--output"}:
            if index + 1 >= len(argv):
                raise ValueError(f"missing value for {arg}")
            value = Path(argv[index + 1])
            if arg == "--options":
                options_path = value
            else:
                output_path = value
            index += 2
            continue

        raise ValueError(f"unknown argument: {arg}")

    if options_path is None:
        raise ValueError("--options is required")
    if output_path is None:
        raise ValueError("--output is required")
    return options_path, output_path, print_redacted


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def normalize_string(value: object | None, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def map_autonomy_level(value: object | None) -> str:
    mapped = normalize_string(value, "supervised").strip()
    if mapped == "read_only":
        return "readonly"
    if mapped in {"readonly", "supervised", "full"}:
        return mapped
    return "supervised"


def normalize_allowed_users(value: object) -> list[str]:
    if isinstance(value, list):
        users: list[str] = []
        for item in value:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(item, str) and item:
                users.append(item)
        if users:
            return users
    return ["*"]


def missing_required_keys(options: dict[str, object]) -> list[str]:
    required_keys = ["api_key", "telegram_bot_token"]
    missing: list[str] = []
    for key in required_keys:
        value = options.get(key)
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
    return missing


def bool_option(options: dict[str, object], key: str, default: bool = False) -> bool:
    value = options.get(key)
    if isinstance(value, bool):
        return value
    return default


def float_option(
    options: dict[str, object], key: str, default: float
) -> float:
    value = options.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return default


def build_config(options: dict[str, object]) -> str:
    provider = normalize_string(options.get("provider"), "openrouter")
    api_key = normalize_string(options.get("api_key"), "")
    model = options.get("model")
    bot_token = normalize_string(options.get("telegram_bot_token"), "")
    allowed_users = normalize_allowed_users(options.get("telegram_allowed_users"))
    autonomy_level = map_autonomy_level(options.get("autonomy_level"))
    enable_memory = bool_option(options, "enable_memory", True)
    enable_cost = bool_option(options, "enable_cost_tracking", True)
    daily_cost = float_option(options, "daily_cost_limit_usd", 2.0)

    model_line = ""
    if isinstance(model, str) and model.strip():
        model_line = f"default_model = {toml_string(model)}"

    config_text = f"""\
default_provider = {toml_string(provider)}
api_key = {toml_string(api_key)}
default_temperature = 0.7
{model_line}

[channels_config]
cli = false

[channels_config.telegram]
bot_token = {toml_string(bot_token)}
allowed_users = {json.dumps(allowed_users, ensure_ascii=False)}

[autonomy]
level = {toml_string(autonomy_level)}
allowed_commands = ["ha_api"]
workspace_only = true
forbidden_paths = []
max_actions_per_hour = 120
max_cost_per_day_cents = 500
shell_env_passthrough = ["SUPERVISOR_TOKEN", "HA_API_ALLOW_COVER", "HA_API_ALLOW_SCRIPT", "HA_API_ALLOW_AUTOMATION", "HA_API_ALLOW_EVENT"]

[agent]
max_tool_iterations = 15
max_history_messages = 50

[cron]
enabled = true

[scheduler]
enabled = true
max_tasks = 64
max_concurrent = 4
"""

    if enable_memory:
        config_text += """
[memory]
backend = "sqlite"
auto_save = true
"""

    if enable_cost:
        config_text += f"""
[cost]
enabled = true
daily_limit_usd = {daily_cost:.2f}
monthly_limit_usd = {daily_cost * 31:.2f}
warn_at_percent = 80
"""

    lines = [config_text.strip(), ""]

    return "\n".join(lines)


def redacted_config(config_text: str) -> str:
    redacted: list[str] = []
    for line in config_text.splitlines():
        if line.startswith("api_key = "):
            redacted.append('api_key = "***REDACTED***"')
            continue
        if line.startswith("bot_token = "):
            redacted.append('bot_token = "***REDACTED***"')
            continue
        redacted.append(line)
    return "\n".join(redacted) + "\n"


def main() -> int:
    try:
        options_path, output_path, print_redacted = parse_args(sys.argv[1:])
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    try:
        options_obj: object = json.loads(options_path.read_text(encoding="utf-8"))  # pyright: ignore[reportAny]
    except FileNotFoundError:
        print("ERROR: options file not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("ERROR: options file contains invalid JSON", file=sys.stderr)
        return 1

    if not isinstance(options_obj, dict):
        print("ERROR: options JSON must be an object", file=sys.stderr)
        return 1

    options: dict[str, object] = {}
    for key, value in options_obj.items():  # pyright: ignore[reportUnknownVariableType]
        options[str(key)] = value  # pyright: ignore[reportUnknownArgumentType]

    missing_keys = missing_required_keys(options)
    if missing_keys:
        if len(missing_keys) == 1:
            print(
                f"ERROR: missing required add-on configuration key {missing_keys[0]}. Set it in the Home Assistant add-on configuration UI.",
                file=sys.stderr,
            )
        else:
            print(
                "ERROR: missing required add-on configuration keys: "
                + ", ".join(missing_keys)
                + ". Set them in the Home Assistant add-on configuration UI.",
                file=sys.stderr,
            )
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    config_text = build_config(options)
    _ = output_path.write_text(config_text, encoding="utf-8")

    if print_redacted:
        print(redacted_config(config_text), end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
