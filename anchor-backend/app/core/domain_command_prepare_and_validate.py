from app.core.domain_command_payload_normalize import normalize_domain_command_payload
from app.core.domain_command_validation_summary import summarize_domain_command_validation


def prepare_and_validate_domain_command_payload(
    command_type: str, payload: dict
) -> dict:
    normalized_payload = normalize_domain_command_payload(command_type, payload)
    summary = summarize_domain_command_validation(command_type, normalized_payload)
    return {
        "command_type": command_type,
        "payload": normalized_payload,
        "summary": summary,
    }
