import os
import re
import joblib
import numpy as np
from backend.services.preprocessing import clean_text

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

_model = None
_vectorizer = None
_label_encoder = None

def get_artifacts():
    global _model, _vectorizer, _label_encoder
    if _model is None or _vectorizer is None or _label_encoder is None:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORIZER_PATH) or not os.path.exists(ENCODER_PATH):
            raise FileNotFoundError("Model artifacts not found. Run train_model.py first.")
        _model = joblib.load(MODEL_PATH)
        _vectorizer = joblib.load(VECTORIZER_PATH)
        _label_encoder = joblib.load(ENCODER_PATH)
    return _model, _vectorizer, _label_encoder

CATEGORY_BASE_RISK = {
    "NON_ABUSIVE": 2,
    "TOXIC": 45,
    "BULLYING": 72,
    "SEVERE_BULLYING": 90,
    "HATE_SPEECH": 85,
    "SEXUAL_HARASSMENT": 88,
    "THREAT": 95
}

RECOMMENDED_ACTIONS = {
    "NON_ABUSIVE": "Safe to publish",
    "TOXIC": "Review before publishing",
    "BULLYING": "Block & prompt user edit",
    "SEVERE_BULLYING": "Flag for moderator review",
    "HATE_SPEECH": "Flag for moderator review",
    "SEXUAL_HARASSMENT": "Flag for moderator review",
    "THREAT": "Flag for moderator review & escalate"
}

def calculate_risk_and_severity(category: str, confidence: float, raw_text: str):
    base_risk = CATEGORY_BASE_RISK.get(category, 50)
    
    # Adjust based on confidence
    adjusted_risk = base_risk * (0.5 + 0.5 * confidence)
    
    # Keyword sensitivity escalation
    lower_text = raw_text.lower()
    critical_triggers = ["kill", "murder", "bullet", "shoot", "stab", "die", "nude", "explicit", "bomb", "subhuman"]
    text_terms = set(re.findall(r"[a-z]+", lower_text))
    if any(term in text_terms for term in critical_triggers) and category != "NON_ABUSIVE":
        adjusted_risk = max(adjusted_risk, 85.0)
        
    final_risk = int(min(100, max(0, round(adjusted_risk))))
    
    if final_risk <= 20:
        severity = "LOW"
    elif final_risk <= 50:
        severity = "MODERATE"
    elif final_risk <= 75:
        severity = "HIGH"
    else:
        severity = "CRITICAL"
        
    return final_risk, severity

def generate_explanation(category: str, confidence: float, severity: str, is_uncertain: bool, text: str) -> str:
    if is_uncertain:
        return f"Uncertain prediction (Confidence: {round(confidence*100, 1)}%). The text contains ambiguous language or complex context — human review recommended."
    
    explanations = {
        "NON_ABUSIVE": "The comment uses respectful, neutral, or supportive language without abusive, hostile, or threatening patterns.",
        "TOXIC": "The comment contains rude, disrespectful, or vulgar language likely to degrade online discussion quality.",
        "BULLYING": "The comment exhibits targeted insulting or hostile remarks intended to harass or demean another individual.",
        "SEVERE_BULLYING": "The comment displays severe, repeated, or destructive targeted harassment urging severe emotional or physical distress.",
        "HATE_SPEECH": "The comment contains discriminatory or hostile statements targeting protected groups based on race, religion, gender, or origin.",
        "SEXUAL_HARASSMENT": "The comment contains unwanted sexual remarks, requests for explicit material, or coercive sexual claims.",
        "THREAT": "The comment contains explicit language indicating violence, bodily harm, or physical aggression toward individuals or groups."
    }
    
    base_reason = explanations.get(category, "The comment violated standard community guidelines.")
    return f"{base_reason} (Severity: {severity}, Risk Level: {severity.title()})."

def predict_text(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Comment text cannot be empty.")
    if len(text) > 1000:
        raise ValueError("Comment exceeds the maximum allowed length of 1000 characters.")
        
    model, vectorizer, label_encoder = get_artifacts()
    cleaned = clean_text(text)
    
    # Handle edge case: empty after cleaning (e.g. only symbols/numbers)
    if not cleaned:
        cleaned = text.lower()
        
    vec = vectorizer.transform([cleaned])
    probabilities = model.predict_proba(vec)[0]
    best_idx = np.argmax(probabilities)
    confidence = float(probabilities[best_idx])
    category = str(label_encoder.inverse_transform([best_idx])[0])
    
    risk_score, severity = calculate_risk_and_severity(category, confidence, text)
    # Low-severity comments do not need human verification, even if model
    # confidence is below the uncertainty threshold.
    is_uncertain = confidence < 0.60 and severity != "LOW"
    if severity == "LOW":
        action = "Safe to publish" if category == "NON_ABUSIVE" else "No human review required"
    else:
        action = RECOMMENDED_ACTIONS.get(category, "Review before publishing")
    explanation = generate_explanation(category, confidence, severity, is_uncertain, text)
    
    return {
        "text": text,
        "category": category,
        "confidence": round(confidence, 4),
        "risk_score": risk_score,
        "severity": severity,
        "explanation": explanation,
        "recommended_action": action,
        "is_uncertain": is_uncertain
    }
