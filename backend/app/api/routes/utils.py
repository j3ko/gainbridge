from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/utils", tags=["utils"])


@router.get("/health-check/")
async def health_check() -> bool:
    return True


class AppConfig(BaseModel):
    timezone: str


@router.get("/config/")
async def get_config() -> AppConfig:
    return AppConfig(timezone=settings.TIMEZONE)
