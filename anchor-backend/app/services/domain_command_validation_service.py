from app.core.domain_command_prepare_and_validate import (
    prepare_and_validate_domain_command_payload,
)


def validate_domain_command_for_dev(command_type: str, payload: dict) -> dict:
    return prepare_and_validate_domain_command_payload(command_type, payload)
