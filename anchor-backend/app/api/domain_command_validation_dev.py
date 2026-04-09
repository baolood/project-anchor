from app.services.domain_command_validation_service import validate_domain_command_for_dev


def run_domain_command_validation_dev(command_type: str, payload: dict) -> dict:
    return validate_domain_command_for_dev(command_type, payload)
