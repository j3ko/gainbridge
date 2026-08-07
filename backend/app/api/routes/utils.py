from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr
from app.models import Message

router = APIRouter(prefix="/utils", tags=["utils"])

@router.get("/health-check/")
async def health_check() -> bool:
    return True
