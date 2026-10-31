from fastapi import APIRouter, HTTPException, status
from backend.database.models import PredictionRequest, PredictionResponse
from backend.services.prediction_service import predict_text

router = APIRouter(prefix="/api", tags=["Prediction"])

@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Analyze Social Media Comment",
    description="Analyzes input comment text and returns predicted classification category, confidence score, risk score (0-100), severity level, human-readable explanation, and recommended moderation action."
)
def predict_comment(request: PredictionRequest):
    try:
        result = predict_text(request.text)
        return PredictionResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to analyze the comment. Please try again.")
