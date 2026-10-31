import re
# pyrefly: ignore [missing-import]
import nltk
# pyrefly: ignore [missing-import]
from nltk.corpus import stopwords
# pyrefly: ignore [missing-import]
from nltk.stem import WordNetLemmatizer

def download_nltk_data():
    for resource in ['stopwords', 'wordnet', 'omw-1.4']:
        try:
            nltk.data.find(f'corpora/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

download_nltk_data()
lemmatizer = WordNetLemmatizer()

try:
    # Preserve negation because it can reverse whether a statement is harmful.
    stop_words = set(stopwords.words('english')) - {"no", "nor", "not"}
except Exception:
    stop_words = set()

def clean_text(text: str) -> str:
    """
    Standard text normalization pipeline:
    - Lowercasing
    - Strip URLs, mentions, hashtags
    - Remove non-alphabetic symbols
    - Tokenization & stopword removal
    - WordNet Lemmatization
    """
    if not text or not isinstance(text, str):
        return ""
    
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'@[A-Za-z0-9_]+', '', text)
    text = re.sub(r'#[A-Za-z0-9_]+', '', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    
    tokens = text.split()
    cleaned = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words and len(word) > 1]
    return " ".join(cleaned)
