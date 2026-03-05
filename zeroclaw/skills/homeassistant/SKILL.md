# Home Assistant Skill

Use `ha_api` as the only Home Assistant control interface.

## Discovery First
- Start with snapshot files when available:
  - `$ZEROCLAW_WORKSPACE/homeassistant/states.json`
  - `$ZEROCLAW_WORKSPACE/homeassistant/services.json`
- If snapshots are missing or stale, run:
  - `ha_api list-states`
  - `ha_api list-services`

## Entity Resolution
- Resolve `friendly_name` to `entity_id` before any action.
- If multiple entities match a name, ask the user to disambiguate.

## Safety Boundaries
- Never operate entities in `lock.*` or `alarm_control_panel.*`.
- Never call restart, shutdown, or reboot services.

## Action Policy
- Prefer scenes for user intent when possible.
- Use scripts only when the user explicitly enabled `allow_script`.
- Perform actuation only with:
  - `ha_api call-service <domain> <service> --json '{...}'`

## Reporting
- Always report back the exact `entity_id` and `<domain>.<service>` used.

## Examples
```bash
ha_api call-service light turn_on --json '{"entity_id":"light.kitchen","brightness_pct":60}'
ha_api call-service scene turn_on --json '{"entity_id":"scene.evening_relax"}'
```
