from fastapi import APIRouter

from .designer_tasks.designers import router as designers_router
from .designer_tasks.media_buyer_teams import router as media_buyer_teams_router
from .media_buyers.media_buyer_tasks_statistics import router as media_buyer_tasks_statistics_router

statistics = APIRouter(
    prefix="/statistic",
    tags=["Statistics"],
)

statistics.include_router(designers_router)
statistics.include_router(media_buyer_teams_router)
statistics.include_router(media_buyer_tasks_statistics_router)
