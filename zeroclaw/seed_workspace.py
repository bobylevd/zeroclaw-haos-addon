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
    "brightness_pct",
    "brightness",
    "color_mode",
    "effect",
    "min_mireds",
    "max_mireds",
}
SECRET_KEYWORDS = (
    "token",
    "password",
    "secret",
    "api_key",
    "access",
    "auth",
)
BASE_COMMON_DOMAINS = [
    "light", "switch", "scene", "fan", "climate", "media_player",
    "cover", "binary_sensor", "sensor", "input_boolean", "input_number",
    "input_select", "humidifier", "vacuum", "water_heater", "remote",
    "button", "number", "select",
]


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


def run_ha_api(command, extra_args=None):
    cmd = ["ha_api", command]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
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


def run_ha_api_optional(command, extra_args=None):
    try:
        return run_ha_api(command, extra_args)
    except RuntimeError:
        return None


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


def state_summary(item):
    state = item.get("state", "unknown")
    attrs = item.get("attributes", {})
    if not isinstance(attrs, dict):
        attrs = {}
    parts = [state]
    unit = attrs.get("unit_of_measurement")
    if isinstance(unit, str) and unit:
        parts = [f"{state} {unit}"]
    brightness = attrs.get("brightness_pct") if "brightness_pct" in attrs else None
    if brightness is not None:
        parts.append(f"brightness:{brightness}%")
    current_temp = attrs.get("current_temperature")
    if current_temp is not None:
        parts.append(f"current:{current_temp}")
    return ", ".join(parts)


def render_inventory(states, areas):
    state_map = {}
    for item in states:
        eid = item.get("entity_id", "")
        if eid:
            state_map[eid] = item

    domain_counts = {}
    for eid in state_map:
        domain = domain_for_entity(eid)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    lines = ["# Home Assistant Context", ""]
    lines.append("## Entity Summary")
    lines.append("")
    for domain in sorted(domain_counts):
        lines.append(f"- {domain}: {domain_counts[domain]}")
    lines.append("")

    assigned_entities = set()

    if areas:
        for area in sorted(areas, key=lambda a: a.get("name", "")):
            area_name = area.get("name", area.get("id", "unknown"))
            area_entities = area.get("entities", [])
            if not area_entities:
                continue

            lines.append(f"## {area_name}")
            lines.append("")
            lines.append("| entity_id | friendly_name | state |")
            lines.append("| --- | --- | --- |")

            rows = []
            for eid in area_entities:
                if not isinstance(eid, str):
                    continue
                assigned_entities.add(eid)
                item = state_map.get(eid)
                if item is None:
                    continue
                domain = domain_for_entity(eid)
                if domain not in BASE_COMMON_DOMAINS and domain != "script":
                    continue
                attrs = item.get("attributes", {})
                fname = attrs.get("friendly_name", "") if isinstance(attrs, dict) else ""
                summary = state_summary(item)
                rows.append((eid, fname, summary))

            rows.sort(key=lambda r: r[0])
            for eid, fname, summary in rows:
                safe_fname = str(fname).replace("|", "\\|")
                safe_eid = eid.replace("|", "\\|")
                safe_summary = summary.replace("|", "\\|")
                lines.append(f"| {safe_eid} | {safe_fname} | {safe_summary} |")
            lines.append("")

    unassigned = []
    for item in states:
        eid = item.get("entity_id", "")
        if eid in assigned_entities or not eid:
            continue
        domain = domain_for_entity(eid)
        if domain not in BASE_COMMON_DOMAINS and domain != "script":
            continue
        attrs = item.get("attributes", {})
        fname = attrs.get("friendly_name", "") if isinstance(attrs, dict) else ""
        summary = state_summary(item)
        unassigned.append((eid, fname, summary))

    if unassigned:
        lines.append("## Unassigned Entities")
        lines.append("")
        lines.append("| entity_id | friendly_name | state |")
        lines.append("| --- | --- | --- |")
        unassigned.sort(key=lambda r: r[0])
        for eid, fname, summary in unassigned:
            safe_fname = str(fname).replace("|", "\\|")
            safe_eid = eid.replace("|", "\\|")
            safe_summary = summary.replace("|", "\\|")
            lines.append(f"| {safe_eid} | {safe_fname} | {safe_summary} |")
        lines.append("")

    scenes = [s for s in states if domain_for_entity(s.get("entity_id", "")) == "scene"]
    if scenes:
        lines.append("## Available Scenes")
        lines.append("")
        for s in sorted(scenes, key=lambda x: x.get("entity_id", "")):
            eid = s.get("entity_id", "")
            attrs = s.get("attributes", {})
            fname = attrs.get("friendly_name", eid) if isinstance(attrs, dict) else eid
            lines.append(f"- `{eid}` — {fname}")
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

    raw_areas = run_ha_api_optional("list-areas")
    areas = raw_areas if isinstance(raw_areas, list) else []

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
    if areas:
        areas_path = snapshot_dir / "areas.json"
        write_json(areas_path, areas)
    inventory_path.write_text(
        render_inventory(sanitized_states, areas), encoding="utf-8"
    )

    print(f"Seeded Home Assistant snapshot at {snapshot_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
