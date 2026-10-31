from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class PredictionRequest(BaseModel):
    text: str = Field(..., example="You are such an idiot.", min_length=1, max_length=1000)

class PredictionResponse(BaseModel):
    text: str
    category: str
    confidence: float
    risk_score: int
    severity: str
    explanation: str
    recommended_action: str
    is_uncertain: bool = False

class ModerationRequest(BaseModel):
    text: str = Field(..., example="Check out my new post!", min_length=1, max_length=1000)
    username: str = Field("User123", example="User123")

class ModerationResponse(BaseModel):
    allowed: bool
    category: str
    confidence: float
    is_uncertain: bool = False
    severity: str
    risk_score: int
    action: str
    message: str
    comment_id: Optional[str] = None
    explanation: Optional[str] = None

class QueueActionRequest(BaseModel):
    comment_id: str
    action: str = Field(..., example="APPROVE") # APPROVE, REMOVE, MARK_SAFE, ESCALATE
    performed_by: str = Field("Moderator_Admin", example="Admin")
    notes: Optional[str] = None

class CommentRecord(BaseModel):
    id: int
    comment_id: str
    username: str
    text: str
    category: str
    confidence: float
    risk_score: int
    severity: str
    recommended_action: str
    status: str
    created_at: str
    reviewed_at: Optional[str] = None
    notes: Optional[str] = None

class AnalyticsResponse(BaseModel):
    total_comments: int
    safe_comments: int
    toxic_comments: int
    bullying_comments: int
    severe_bullying_comments: int
    hate_speech_comments: int
    sexual_harassment_comments: int
    threat_comments: int
    flagged_comments: int
    average_confidence: float
    category_percentages: Dict[str, float]
    severity_breakdown: Dict[str, int]
    activity_labels: List[str]
    comments_by_day: List[int]
    flagged_by_day: List[int]
    status_breakdown: Dict[str, int]
