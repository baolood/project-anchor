from fastapi import APIRouter
from app.api.commands import router as commands_router

router = APIRouter()
router.include_router(commands_router)
