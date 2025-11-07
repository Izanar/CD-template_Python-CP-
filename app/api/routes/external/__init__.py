from fastapi import APIRouter

from .creative import creative_router

external_api_router = APIRouter(
    prefix="/api/v1/external",
    tags=["External API"],
)

external_api_router.include_router(creative_router)

__all__ = ["external_api_router"]
