from fastapi import APIRouter, HTTPException, status
from backend.database.models import AnalyticsResponse
from backend.services.moderation_service import get_analytics_metrics

router = APIRouter(prefix="/api", tags=["Analytics"])

@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get Analytics & Metrics Summary",
    description="Returns aggregate counts, category distribution percentages, severity breakdown, average confidence score, and moderation metrics for dashboard charts."
)
def fetch_analytics():
    try:
        metrics = get_analytics_metrics()
        return AnalyticsResponse(**metrics)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to calculate analytics metrics.")
