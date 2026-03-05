#!/usr/bin/python3

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_WORKSPACE = "/data/workspace"
DEFAULT_MAX_AGE_HOURS = 24
SAFE_STATE_ATTRIBUTES = {
    "friendly_name",
    "device_class",
    "icon",
    "unit_of_measurement",
    "state_class",
    "supported_features",
    "hvac_modes",
    "temperature_unit",
    "current_temperature",
    "target_temp_high",
    "target_temp_low",
}
SECRET_KEYWORDS = (
    "token",
    "password",
    "secret",
    "api_key",
    "access",
    "auth",
)
BASE_COMMON_DOMAINS = ["light", "switch", "scene", "fan", "climate", "media_player"]


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Seed Home Assistant workspace snapshots")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("ZEROCLAW_WORKSPACE", DEFAULT_WORKSPACE),
        help="Workspace root (default: ZEROCLAW_WORKSPACE or /data/workspace)",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=int(os.environ.get("ZEROCLAW_SNAPSHOT_MAX_AGE_HOURS", DEFAULT_MAX_AGE_HOURS)),
        help="Maximum snapshot age in hours before refresh",
    )
    return parser.parse_args()


def contains_secret_key(key):
    lowered = key.lower()
    return any(keyword in lowered for keyword in SECRET_KEYWORDS)


def clamp_string(value, limit=200):
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def sanitize_value(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return clamp_string(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value[:20]]
    return clamp_string(str(value))


def sanitize_state(item):
    entity_id = item.get("entity_id")
    if not isinstance(entity_id, str) or "." not in entity_id:
        return None

    attributes = item.get("attributes")
    safe_attributes = {}
    if isinstance(attributes, dict):
        for key in SAFE_STATE_ATTRIBUTES:
            if key in attributes and not contains_secret_key(key):
                safe_attributes[key] = sanitize_value(attributes[key])

    return {
        "entity_id": entity_id,
        "state": sanitize_value(item.get("state")),
        "last_changed": sanitize_value(item.get("last_changed")),
        "last_updated": sanitize_value(item.get("last_updated")),
        "attributes": safe_attributes,
    }


def sanitize_services(raw_services):
    sanitized = []
    if not isinstance(raw_services, list):
        return sanitized

    for domain_entry in raw_services:
        domain = domain_entry.get("domain")
        services = domain_entry.get("services")
        if not isinstance(domain, str) or not isinstance(services, dict):
            continue

        safe_services = {}
        for service_name, service_data in sorted(services.items()):
            if contains_secret_key(service_name):
                continue

            description = ""
            field_names = []
            if isinstance(service_data, dict):
                raw_description = service_data.get("description")
                if isinstance(raw_description, str):
                    description = clamp_string(raw_description, 240)

                raw_fields = service_data.get("fields")
                if isinstance(raw_fields, dict):
                    for field_name in sorted(raw_fields.keys()):
                        if not contains_secret_key(str(field_name)):
                            field_names.append(str(field_name))

            safe_services[service_name] = {
                "description": description,
                "fields": field_names[:40],
            }

        sanitized.append({"domain": domain, "services": safe_services})

    return sanitized


def run_ha_api(command):
    proc = subprocess.run(
        ["ha_api", command],
        check=False,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown ha_api error"
        raise RuntimeError(f"ha_api {command} failed: {detail}")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        raise RuntimeError(f"ha_api {command} returned invalid JSON: {err.msg}") from err


def write_json(path, payload):
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    temp_path.replace(path)


def is_fresh(snapshot_files, max_age_seconds):
    for file_path in snapshot_files:
        if not file_path.exists():
            return False

    now = time.time()
    oldest_mtime = min(file_path.stat().st_mtime for file_path in snapshot_files)
    return now - oldest_mtime <= max_age_seconds


def domain_for_entity(entity_id):
    return entity_id.split(".", 1)[0]


def render_inventory(states):
    domain_counts = {}
    present_domains = set()

    for item in states:
        entity_id = item.get("entity_id", "")
        if "." not in entity_id:
            continue
        domain = domain_for_entity(entity_id)
        present_domains.add(domain)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    ordered_domains = BASE_COMMON_DOMAINS[:]
    for optional_domain in ("cover", "script"):
        if optional_domain in present_domains:
            ordered_domains.append(optional_domain)

    lines = ["# Home Assistant Inventory", "", "## Entity Counts by Domain", ""]
    for domain in sorted(domain_counts):
        lines.append(f"- {domain}: {domain_counts[domain]}")

    lines.append("")
    for domain in ordered_domains:
        rows = []
        for item in states:
            entity_id = item.get("entity_id", "")
            if not entity_id.startswith(f"{domain}."):
                continue
            attributes = item.get("attributes", {})
            friendly_name = attributes.get("friendly_name") if isinstance(attributes, dict) else None
            label = friendly_name if isinstance(friendly_name, str) and friendly_name else entity_id
            rows.append((label, entity_id))

        if not rows:
            continue

        rows.sort(key=lambda value: (value[0].lower(), value[1]))
        lines.append(f"## {domain}")
        lines.append("")
        lines.append("| friendly_name | entity_id |")
        lines.append("| --- | --- |")
        for label, entity_id in rows:
            safe_label = label.replace("|", "\\|")
            safe_entity = entity_id.replace("|", "\\|")
            lines.append(f"| {safe_label} | {safe_entity} |")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main():
    args = parse_args()
    if args.max_age_hours < 1:
        return fail("max-age-hours must be >= 1")

    workspace = Path(args.workspace)
    snapshot_dir = workspace / "homeassistant"
    states_path = snapshot_dir / "states.json"
    services_path = snapshot_dir / "services.json"
    inventory_path = snapshot_dir / "inventory.md"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    max_age_seconds = args.max_age_hours * 3600
    snapshot_files = [states_path, services_path, inventory_path]
    if is_fresh(snapshot_files, max_age_seconds):
        print("Workspace snapshot is fresh; skipping seed.")
        return 0

    try:
        raw_states = run_ha_api("list-states")
        raw_services = run_ha_api("list-services")
    except RuntimeError as err:
        return fail(str(err))

    if not isinstance(raw_states, list):
        return fail("ha_api list-states returned non-list JSON")

    sanitized_states = []
    for item in raw_states:
        if isinstance(item, dict):
            sanitized = sanitize_state(item)
            if sanitized is not None:
                sanitized_states.append(sanitized)

    sanitized_states.sort(key=lambda entry: entry["entity_id"])
    sanitized_services = sanitize_services(raw_services)
    sanitized_services.sort(key=lambda entry: entry.get("domain", ""))

    write_json(states_path, sanitized_states)
    write_json(services_path, sanitized_services)
    inventory_path.write_text(render_inventory(sanitized_states), encoding="utf-8")

    print(f"Seeded Home Assistant snapshot at {snapshot_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
