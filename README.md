# CyberShield AI: Cyberbullying Detection & Social Media Comment Moderation

**CyberShield AI** is a local demonstration of social media comment moderation using a small synthetic NLP dataset and a FastAPI backend. It classifies comments into seven risk categories, calculates risk scores, assigns severity levels, and provides human-readable explanations. Treat predictions as demonstrations and do not use them as the sole basis for real moderation decisions.

---

## 🌟 Key Features

1. **7-Class Granular NLP Classification**:
   - `NON_ABUSIVE` 🟢 (Safe, constructive comments)
   - `TOXIC` 🟡 (Rude, disrespectful, or vulgar language)
   - `BULLYING` 🟠 (Targeted insult or demeaning remarks)
   - `SEVERE_BULLYING` 🔴 (Urgings of self-harm, severe harassment)
   - `HATE_SPEECH` 🟣 (Discriminatory statements targeting protected groups)
   - `SEXUAL_HARASSMENT` 💗 (Unwanted sexual claims, explicit coercion)
   - `THREAT` 🚨 (Explicit violence, weapons, or physical assault threats)

2. **Real-Time Keystroke Moderation**:
   - 600ms debounced input preview on the frontend with live status indicator ("Analyzing...", "✓ Safe to publish", or "⚠ Potentially harmful language").

3. **Explainable AI (XAI)**:
   - Returns clear, human-readable rationales describing detected linguistic patterns without making unsubstantiated claims about user intent.

4. **False Positive & Uncertainty Guard**:
   - Predictions below 60% confidence are automatically flagged with `"Uncertain prediction — human review recommended"` to prevent false removals.

5. **Interactive Pre-Publish Moderation Flow**:
   - Low-risk comments are allowed immediately.
   - Harassment/toxic comments trigger an interactive pre-publish modal allowing the user to **Edit Comment**, **Cancel**, or **Submit for Review**.

6. **Admin & Moderator Analytics Dashboard**:
   - Built with **Chart.js** featuring category doughnut distribution, severity breakdown, comments activity timeline, and live stat counters.

7. **Audit & Moderation Queue**:
   - Searchable moderation table allowing moderators to inspect comments, **Approve**, **Remove**, **Mark Safe**, or **Escalate** items.

---

## 🏗️ Architecture & NLP Pipeline

```
Social Media Comment Text
         │
         ▼
[ Text Preprocessing & Cleaning ] ──► (Lowercasing, Regex URL/Mention Stripping)
         │
         ▼
[ NLTK Tokenization & Lemmatization ] ──► (WordNet Lemmatization + Stopwords Filter)
         │
         ▼
[ TF-IDF Vectorizer (ngram 1-2) ] ──► (Feature Extraction, 10,000 max features)
         │
         ▼
[ Calibrated Classifier + Logistic Regression ] ──► (Calibrated Probability Matrix)
         │
         ▼
[ Risk Scoring & Policy Engine ] ──► (Category, Confidence, Risk 0-100, Severity)
         │
         ▼
[ SQLite Database & Audit Log ] ──► (Persisted Comments & Queue States)
```

---

## 🛠️ Installation & Setup Guide

### 1. Install Dependencies
Ensure Python 3.10+ is installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Train the Machine Learning Model
To train the TF-IDF + Calibrated Classifier model on the dataset and save serialized artifacts (`model.pkl`, `vectorizer.pkl`, `label_encoder.pkl`):
```bash
python train_model.py
```

### 3. Run Automated System Unit Tests
To verify all classification categories, risk scoring, edge cases, SQLite operations, and analytics:
```bash
python test_system.py
```

### 4. Start the FastAPI Backend Server
Launch the production server using Uvicorn:
```bash
python -m uvicorn backend.app:app --reload --port 8000
```

---

## 🌐 Opening the Frontend

Once the FastAPI backend is running on `http://127.0.0.1:8000`, open your web browser to access the following interfaces:

- **AI Sandbox & Live Tester**: [`http://127.0.0.1:8000/static/index.html`](http://127.0.0.1:8000/static/index.html)
- **Social Media Feed Mock**: [`http://127.0.0.1:8000/static/feed.html`](http://127.0.0.1:8000/static/feed.html)
- **Admin Analytics Dashboard**: [`http://127.0.0.1:8000/static/dashboard.html`](http://127.0.0.1:8000/static/dashboard.html)
- **Moderation Queue Interface**: [`http://127.0.0.1:8000/static/moderation.html`](http://127.0.0.1:8000/static/moderation.html)

---

## 📡 API Reference & Documentation

FastAPI provides interactive API documentation out of the box:
- **Swagger UI**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **ReDoc**: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

### Core Endpoints

#### 1. Prediction API
`POST /api/predict`
- **Request Body**:
  ```json
  {
    "text": "You are such an idiot."
  }
  ```
- **Response**:
  ```json
  {
    "text": "You are such an idiot.",
    "category": "TOXIC",
    "confidence": 0.9421,
    "risk_score": 52,
    "severity": "MODERATE",
    "explanation": "The comment contains rude, disrespectful, or vulgar language likely to degrade online discussion quality. (Severity: MODERATE, Risk Level: Moderate).",
    "recommended_action": "Review before publishing",
    "is_uncertain": false
  }
  ```

#### 2. Pre-Publication Moderation API
`POST /api/moderate`
- **Request Body**:
  ```json
  {
    "text": "I will find you and shoot you in the head.",
    "username": "User123"
  }
  ```
- **Response**:
  ```json
  {
    "allowed": false,
    "category": "THREAT",
    "confidence": 0.9912,
    "severity": "CRITICAL",
    "risk_score": 99,
    "action": "FLAG_FOR_REVIEW",
    "message": "This comment contains severe threat indicators and has been flagged for urgent moderator review.",
    "comment_id": "CMT-A8F2E1",
    "explanation": "The comment contains explicit language indicating violence, bodily harm, or physical aggression..."
  }
  ```

#### 3. Analytics API
`GET /api/analytics`
- Returns aggregate metrics, category distribution percentages, severity breakdown, and average confidence.

#### 4. Moderation Queue API
`GET /api/moderation/queue?status=FLAGGED&search=query`
- Returns list of flagged comments for moderator review.

#### 5. Moderator Action API
`POST /api/moderation/action`
- Accepts `comment_id` and action (`APPROVE`, `REMOVE`, `MARK_SAFE`, `ESCALATE`) and updates SQLite database audit logs.

---

## 🔒 Security & Privacy

- **Input Sanitization & XSS Prevention**: All frontend comment previews escape HTML entities (`&`, `<`, `>`, `"`, `'`).
- **Input Validation**: Text length is validated (1-1000 characters).
- **Privacy**: The demo stores submitted comment text and usernames in its local SQLite database. Do not enter real personal or sensitive information.

---

## Model Evaluation Metrics

The current synthetic dataset contains 300 examples. A stratified 80/20 split evaluates the model on 60 held-out examples. The latest training run reported these scores; they are a small-demo benchmark and do not establish real-world performance.

| Metric | Score |
|---|---|
| **Accuracy** | **81.67%** |
| **Weighted Precision** | **84.26%** |
| **Weighted Recall** | **81.67%** |
| **Weighted F1-Score** | **82.31%** |
| **Threat F1-Score** | **0.88** |
| **Hate Speech F1-Score** | **0.88** |
| **Sexual Harassment F1-Score** | **1.00** |
