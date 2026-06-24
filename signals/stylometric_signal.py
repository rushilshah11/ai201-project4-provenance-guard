import re
import string


def run_stylometric_signal(text: str) -> dict:
    """Analyze text structure for AI-likelihood using pure Python heuristics.

    Three metrics averaged into a score between 0 (human) and 1 (AI):
      1. Sentence length variance — low variance → high AI score
      2. Type-token ratio — low lexical diversity → high AI score
      3. Punctuation density — low punctuation → high AI score

    Returns a dict with 'score' (float 0–1).
    """
    scores = []

    # --- Metric 1: Sentence length variance ---
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if len(sentences) >= 2:
        lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        scores.append(1 - min(variance, 400) / 400)
    else:
        scores.append(0.5)

    # --- Metric 2: Type-token ratio ---
    words = re.findall(r"\b\w+\b", text.lower())
    if words:
        ttr = len(set(words)) / len(words)
        scores.append(1 - ttr)
    else:
        scores.append(0.5)

    # --- Metric 3: Punctuation density ---
    total_chars = len(text)
    if total_chars > 0:
        punct_count = sum(1 for c in text if c in string.punctuation)
        density = punct_count / total_chars
        scores.append(1 - min(density, 0.2) / 0.2)
    else:
        scores.append(0.5)

    return {"score": round(sum(scores) / len(scores), 4)}
