import sqlite3
from datetime import datetime, timedelta
import uuid
from backend.database.database import get_db_connection
from backend.services.prediction_service import predict_text

ACTION_MAP = {
    "NON_ABUSIVE": "ALLOW",
    "TOXIC": "ALLOW_WITH_WARNING",
    "BULLYING": "BLOCK_PROMPT_EDIT",
    "SEVERE_BULLYING": "FLAG_FOR_REVIEW",
    "HATE_SPEECH": "FLAG_FOR_REVIEW",
    "SEXUAL_HARASSMENT": "FLAG_FOR_REVIEW",
    "THREAT": "FLAG_FOR_REVIEW"
}

STATUS_MAP = {
    "ALLOW": "APPROVED",
    "ALLOW_WITH_WARNING": "APPROVED",
    "BLOCK_PROMPT_EDIT": "PENDING_REVIEW",
    "FLAG_FOR_REVIEW": "FLAGGED"
}

def process_comment_moderation(text: str, username: str = "User123") -> dict:
    prediction = predict_text(text)
    
    category = prediction["category"]
    confidence = prediction["confidence"]
    is_uncertain = prediction["is_uncertain"]
    risk_score = prediction["risk_score"]
    severity = prediction["severity"]

    if is_uncertain:
        action = "FLAG_FOR_REVIEW"
        status = "PENDING_REVIEW"
        message = "The model is uncertain, so this comment was held for human review."
    else:
        action = ACTION_MAP.get(category, "FLAG_FOR_REVIEW")
        status = STATUS_MAP.get(action, "FLAGGED")

    allowed = action in {"ALLOW", "ALLOW_WITH_WARNING"}

    # Message for frontend modal/alert
    if is_uncertain:
        pass
    elif category == "NON_ABUSIVE":
        message = "Comment is safe and ready to publish."
    elif category == "TOXIC":
        message = "This comment contains potentially toxic language. Please consider revising."
    elif category in ["BULLYING", "SEVERE_BULLYING"]:
        message = "This comment may violate our community guidelines on harassment. Please review your comment before posting."
    elif category == "HATE_SPEECH":
        message = "This comment has been flagged by our AI moderation system for hateful language and requires review."
    elif category == "SEXUAL_HARASSMENT":
        message = "This comment has been flagged for explicit or sexually coercive content."
    elif category == "THREAT":
        message = "This comment contains severe threat indicators and has been flagged for urgent moderator review."
    else:
        message = "Comment flagged by AI moderation system."
        
    comment_id = f"CMT-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO comments (comment_id, username, text, category, confidence, risk_score, severity, recommended_action, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (comment_id, username, text, category, confidence, risk_score, severity, action, status, now_str))
    conn.commit()
    conn.close()
    
    return {
        "allowed": allowed,
        "category": category,
        "confidence": confidence,
        "is_uncertain": is_uncertain,
        "severity": severity,
        "risk_score": risk_score,
        "action": action,
        "message": message,
        "comment_id": comment_id,
        "explanation": prediction["explanation"]
    }

def get_moderation_queue(status_filter: str = None, search: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM comments WHERE 1=1"
    params = []
    
    if status_filter and status_filter.upper() != "ALL":
        query += " AND status = ?"
        params.append(status_filter.upper())
        
    if search:
        query += " AND (text LIKE ? OR username LIKE ? OR comment_id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    comments = [dict(row) for row in rows]
    return comments

def update_comment_status(comment_id: str, action: str, performed_by: str = "Admin", notes: str = None):
    action = action.upper()
    if action not in {"APPROVE", "MARK_SAFE", "REMOVE", "ESCALATE"}:
        raise ValueError(f"Unsupported moderation action: {action}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()

    if action == "REMOVE":
        # Keep the record for the Removed queue and audit history.
        new_status = "REMOVED"
        cursor.execute("""
            UPDATE comments
            SET status = ?, reviewed_at = ?, notes = ?
            WHERE comment_id = ?
        """, (new_status, now_str, notes, comment_id))
        if cursor.rowcount == 0:
            conn.close()
            raise LookupError(f"Comment {comment_id} was not found.")
    else:
        new_status = "PENDING_REVIEW"
        if action in {"APPROVE", "MARK_SAFE"}:
            new_status = "APPROVED"
        elif action == "ESCALATE":
            new_status = "UNDER_REVIEW"

        cursor.execute("""
            UPDATE comments
            SET status = ?, reviewed_at = ?, notes = ?
            WHERE comment_id = ?
        """, (new_status, now_str, notes, comment_id))
        if cursor.rowcount == 0:
            conn.close()
            raise LookupError(f"Comment {comment_id} was not found.")

    cursor.execute("""
        INSERT INTO audit_logs (comment_id, action, performed_by, timestamp)
        VALUES (?, ?, ?, ?)
    """, (comment_id, action, performed_by, now_str))

    conn.commit()
    conn.close()

    return {
        "comment_id": comment_id,
        "new_status": new_status,
        "removed": action == "REMOVE",
        "action": action,
    }

def get_analytics_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM comments")
    total = cursor.fetchone()['total']

    day_start = datetime.now().date() - timedelta(days=6)
    activity_days = [day_start + timedelta(days=offset) for offset in range(7)]
    cursor.execute("""
        SELECT substr(created_at, 1, 10) AS day,
               COUNT(*) AS total,
               SUM(CASE WHEN status IN ('FLAGGED', 'PENDING_REVIEW', 'UNDER_REVIEW') THEN 1 ELSE 0 END) AS flagged
        FROM comments
        WHERE substr(created_at, 1, 10) >= ?
        GROUP BY substr(created_at, 1, 10)
    """, (day_start.isoformat(),))
    activity_rows = {row['day']: dict(row) for row in cursor.fetchall()}
    activity_labels = [day.strftime("%a %m/%d") for day in activity_days]
    comments_by_day = [activity_rows.get(day.isoformat(), {}).get('total', 0) for day in activity_days]
    flagged_by_day = [activity_rows.get(day.isoformat(), {}).get('flagged', 0) or 0 for day in activity_days]

    cursor.execute("SELECT status, COUNT(*) AS count FROM comments GROUP BY status")
    known_statuses = ["APPROVED", "FLAGGED", "PENDING_REVIEW", "UNDER_REVIEW", "REMOVED"]
    stored_statuses = {row['status']: row['count'] for row in cursor.fetchall()}
    status_breakdown = {key: stored_statuses.get(key, 0) for key in known_statuses}
    
    if total == 0:
        conn.close()
        return {
            "total_comments": 0,
            "safe_comments": 0,
            "toxic_comments": 0,
            "bullying_comments": 0,
            "severe_bullying_comments": 0,
            "hate_speech_comments": 0,
            "sexual_harassment_comments": 0,
            "threat_comments": 0,
            "flagged_comments": 0,
            "average_confidence": 0.0,
            "category_percentages": {},
            "severity_breakdown": {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0},
            "activity_labels": activity_labels,
            "comments_by_day": comments_by_day,
            "flagged_by_day": flagged_by_day,
            "status_breakdown": status_breakdown
        }
        
    def count_cat(cat):
        cursor.execute("SELECT COUNT(*) as cnt FROM comments WHERE category = ?", (cat,))
        return cursor.fetchone()['cnt']
        
    safe_cnt = count_cat("NON_ABUSIVE")
    toxic_cnt = count_cat("TOXIC")
    bullying_cnt = count_cat("BULLYING")
    severe_cnt = count_cat("SEVERE_BULLYING")
    hate_cnt = count_cat("HATE_SPEECH")
    sexual_cnt = count_cat("SEXUAL_HARASSMENT")
    threat_cnt = count_cat("THREAT")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM comments WHERE status IN ('FLAGGED', 'PENDING_REVIEW', 'UNDER_REVIEW')")
    flagged_cnt = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT AVG(confidence) as avg_conf FROM comments")
    avg_conf = cursor.fetchone()['avg_conf'] or 0.0
    
    categories = ["NON_ABUSIVE", "TOXIC", "BULLYING", "SEVERE_BULLYING", "HATE_SPEECH", "SEXUAL_HARASSMENT", "THREAT"]
    percentages = {}
    for cat in categories:
        cnt = count_cat(cat)
        percentages[cat] = round((cnt / total) * 100, 2)
        
    severity_breakdown = {}
    for lev in ["LOW", "MODERATE", "HIGH", "CRITICAL"]:
        cursor.execute("SELECT COUNT(*) as cnt FROM comments WHERE severity = ?", (lev,))
        severity_breakdown[lev] = cursor.fetchone()['cnt']
        
    conn.close()
    
    return {
        "total_comments": total,
        "safe_comments": safe_cnt,
        "toxic_comments": toxic_cnt,
        "bullying_comments": bullying_cnt,
        "severe_bullying_comments": severe_cnt,
        "hate_speech_comments": hate_cnt,
        "sexual_harassment_comments": sexual_cnt,
        "threat_comments": threat_cnt,
        "flagged_comments": flagged_cnt,
        "average_confidence": round(avg_conf, 4),
        "category_percentages": percentages,
        "severity_breakdown": severity_breakdown,
        "activity_labels": activity_labels,
        "comments_by_day": comments_by_day,
        "flagged_by_day": flagged_by_day,
        "status_breakdown": status_breakdown
    }
