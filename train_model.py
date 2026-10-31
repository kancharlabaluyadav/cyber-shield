import os
import re
import pandas as pd
import numpy as np
import joblib
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support, confusion_matrix

# Ensure NLTK data downloaded
def download_nltk_deps():
    for resource in ['stopwords', 'wordnet', 'omw-1.4']:
        try:
            nltk.data.find(f'corpora/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

download_nltk_deps()
lemmatizer = WordNetLemmatizer()
try:
    # Keep negation: removing "not" and "no" reverses the meaning of many comments.
    stop_words = set(stopwords.words('english')) - {"no", "nor", "not"}
except Exception:
    stop_words = set()

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Lowercase
    text = text.lower()
    # Remove URLs, mentions, hashtags symbols
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'@[A-Za-z0-9_]+', '', text)
    text = re.sub(r'#[A-Za-z0-9_]+', '', text)
    # Remove non-alphabetical characters (preserve single spaces)
    text = re.sub(r'[^a-z\s]', ' ', text)
    # Tokenization & Lemmatization
    tokens = text.split()
    cleaned_tokens = [lemmatizer.lemmatize(w) for w in tokens if w not in stop_words and len(w) > 1]
    return " ".join(cleaned_tokens)

def load_dataset1(dataset_dir):
    """Load dataset1's differently structured CSVs into the app's label schema."""
    frames = []
    def add(texts, labels):
        frames.append(pd.DataFrame({"text": texts, "label": labels}))

    # This file has the most specific labels for this Twitter corpus.
    path = os.path.join(dataset_dir, "cyberbullying_tweets.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        label_map = {
            "not_cyberbullying": "NON_ABUSIVE",
            "religion": "HATE_SPEECH", "ethnicity": "HATE_SPEECH",
            "gender": "HATE_SPEECH", "age": "BULLYING",
            "other_cyberbullying": "BULLYING",
        }
        add(df["tweet_text"], df["cyberbullying_type"].map(label_map))

    # Detailed harm types provide sexual harassment and severe harassment examples.
    path = os.path.join(dataset_dir, "CyberBullyingTypesDataset.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, encoding_errors="replace")
        label_map = {
            "Sexual Harassment": "SEXUAL_HARASSMENT",
            "Revenge Porn": "SEXUAL_HARASSMENT",
            "Slut Shaming": "BULLYING",
            "Doxing": "SEVERE_BULLYING", "Cyberstalking": "SEVERE_BULLYING",
        }
        add(df["Tweet"], df["Class"].map(label_map))

    # Binary datasets add general toxic/bullying examples. Prefer more specific
    # labels above where the same text appears in multiple sources.
    path = os.path.join(dataset_dir, "cyberbullying.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, encoding_errors="replace")
        add(df["tweet_text"], df["cyberbullying_type"].map({0: "NON_ABUSIVE", 1: "BULLYING"}))

    # These files contain binary cyberbullying annotations. A positive label
    # means bullying, not generic toxicity; exact duplicates are resolved below.
    for name in ("CyberTrollIEEE.csv", "cybertroll_dataset.csv"):
        path = os.path.join(dataset_dir, name)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding_errors="replace")
            add(df["content"], df["annotation"].map({0: "NON_ABUSIVE", 1: "BULLYING"}))

    # Use only annotations that match the app's categories. "Suicidal" means
    # self-directed suicidal content, not bullying that urges another person
    # to self-harm; "suspicious" is too broad to map reliably.
    path = os.path.join(dataset_dir, "classified_tweets.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, encoding_errors="replace")
        labels = []
        for _, row in df.iterrows():
            if row.get("hate") == 1 or row.get("cyberbullying") in (1, 2):
                labels.append("HATE_SPEECH")
            elif all(row.get(c) == 0 for c in ("suspicious", "cyberbullying", "hate", "suicidal")):
                labels.append("NON_ABUSIVE")
            else:
                labels.append(None)
        add(df["text"], labels)

    if not frames:
        raise FileNotFoundError(f"No supported CSV files found in {dataset_dir}")
    result = pd.concat(frames, ignore_index=True).dropna(subset=["text", "label"])
    result["text"] = result["text"].astype(str).str.strip()
    result = result[result["text"].str.len() > 0]
    return result.drop_duplicates(subset=["text"], keep="first").reset_index(drop=True)

def main():
    print("=" * 60)
    print("      CYBERBULLYING DETECTION - MODEL TRAINING PIPELINE    ")
    print("=" * 60)

    dataset_path = os.path.join("dataset1")
    if os.path.isdir(dataset_path):
        print(f"[1/6] Loading and normalizing CSV files from {dataset_path}...")
        df = load_dataset1(dataset_path)
    else:
        dataset_path = os.path.join("data", "dataset.csv")
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found at {dataset_path} or dataset1/")
        print(f"[1/6] Loading dataset from {dataset_path}...")
        df = pd.read_csv(dataset_path)
    print(f"      Total records loaded: {len(df)}")
    print("      Class distribution:")
    print(df['label'].value_counts())

    # Drop invalid rows
    df = df.dropna(subset=['text', 'label'])
    df['clean_text'] = df['text'].apply(preprocess_text)
    # Deduplicate after normalization too, so casing and punctuation variants
    # cannot land on opposite sides of the train/test split.
    df = df[df['clean_text'].str.len() > 0]
    df = df.drop_duplicates(subset=['clean_text'], keep='first').reset_index(drop=True)

    # Encode Labels
    print("\n[2/6] Encoding target labels...")
    label_encoder = LabelEncoder()
    df['encoded_label'] = label_encoder.fit_transform(df['label'])
    categories = list(label_encoder.classes_)
    print(f"      Classes ({len(categories)}): {categories}")

    # Stratified Train/Test Split
    print("\n[3/6] Splitting train and test sets (Stratified 80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        df['clean_text'],
        df['encoded_label'],
        test_size=0.2,
        random_state=42,
        stratify=df['encoded_label']
    )
    print(f"      Train samples: {len(X_train)} | Test samples: {len(X_test)}")

    # Feature Extraction (TF-IDF)
    print("\n[4/6] Creating TF-IDF Feature Vectors (ngram_range=(1,2))...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=10000,
        sublinear_tf=True
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    print(f"      TF-IDF Matrix shape: {X_train_vec.shape}")

    # Model Training with Probability Calibration
    print("\n[5/6] Training Calibrated Logistic Regression Model...")
    base_lr = LogisticRegression(C=2.0, max_iter=1000, class_weight='balanced', random_state=42)
    model = CalibratedClassifierCV(estimator=base_lr, cv=3)
    model.fit(X_train_vec, y_train)

    # Model Evaluation
    print("\n[6/6] Evaluating Model Performance...")
    y_pred = model.predict(X_test_vec)
    y_proba = model.predict_proba(X_test_vec)

    acc = accuracy_score(y_test, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')

    print("\n" + "=" * 60)
    print(f"  ACCURACY  : {acc:.4f} ({acc*100:.2f}%)")
    print(f"  PRECISION : {prec:.4f}")
    print(f"  RECALL    : {rec:.4f}")
    print(f"  F1-SCORE  : {f1:.4f}")
    print("=" * 60)
    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred, target_names=categories))

    print("Confusion Matrix:\n")
    print(confusion_matrix(y_test, y_pred))

    # Save artifacts
    model_dir = os.path.join("backend", "model")
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, os.path.join(model_dir, "model.pkl"))
    joblib.dump(vectorizer, os.path.join(model_dir, "vectorizer.pkl"))
    joblib.dump(label_encoder, os.path.join(model_dir, "label_encoder.pkl"))

    print(f"\n[SUCCESS] Model artifacts successfully saved to '{model_dir}/':")
    print("  - model.pkl")
    print("  - vectorizer.pkl")
    print("  - label_encoder.pkl")
    print("=" * 60)

if __name__ == "__main__":
    main()
