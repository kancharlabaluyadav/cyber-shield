from fastapi import APIRouter, HTTPException, Query, status as http_status
from typing import Optional, List
from backend.database.models import ModerationRequest, ModerationResponse, QueueActionRequest, CommentRecord
from backend.services.moderation_service import process_comment_moderation, get_moderation_queue, update_comment_status

router = APIRouter(prefix="/api", tags=["Moderation"])

@router.post(
    "/moderate",
    response_model=ModerationResponse,
    summary="Moderate Comment Before Publishing",
    description="Evaluates comment text against social media moderation rules, returns whether publication is allowed immediately, records the entry into database, and determines queue status."
)
def moderate_comment(request: ModerationRequest):
    try:
        res = process_comment_moderation(request.text, request.username)
        return ModerationResponse(**res)
    except ValueError as ve:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to moderate the comment. Please try again.")

@router.get(
    "/moderation/queue",
    response_model=List[CommentRecord],
    summary="Fetch Moderation Queue",
    description="Retrieves comments stored in the moderation queue with optional filtering by status (APPROVED, FLAGGED, PENDING_REVIEW, UNDER_REVIEW, REMOVED) or keyword search."
)
def fetch_queue(
    status: Optional[str] = Query(None, description="Filter by status (e.g. ALL, FLAGGED, PENDING_REVIEW, APPROVED, REMOVED)"),
    search: Optional[str] = Query(None, description="Search query for text, username, or comment ID")
):
    try:
        return get_moderation_queue(status_filter=status, search=search)
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch moderation queue.")

@router.post(
    "/moderation/action",
    summary="Perform Moderator Action",
    description="Approves, escalates, or moves a comment to the Removed queue. Moderator actions are recorded in the audit log."
)
def perform_action(request: QueueActionRequest):
    try:
        res = update_comment_status(request.comment_id, request.action, request.performed_by, request.notes)
        return {"status": "success", "data": res}
    except LookupError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process moderator action.")
