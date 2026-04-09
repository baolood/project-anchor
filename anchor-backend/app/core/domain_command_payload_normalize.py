def normalize_domain_command_payload(command_type: str, payload: dict) -> dict:
    safe_payload = dict(payload) if isinstance(payload, dict) else {}
    safe_payload.setdefault("command_type", command_type)
    return safe_payload
