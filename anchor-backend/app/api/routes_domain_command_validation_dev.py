from fastapi import APIRouter

from app.api.domain_command_validation_dev import run_domain_command_validation_dev

router = APIRouter()


@router.post("/domain-command-validation-dev")
def domain_command_validation_dev(command_type: str, payload: dict) -> dict:
    return run_domain_command_validation_dev(command_type, payload)
