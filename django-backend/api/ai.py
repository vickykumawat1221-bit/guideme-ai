"""AI ranking for GuideMe.

The original implementation embedded a tiny expert string and returned the top 5
cosine matches.  This version is a hybrid ranker:

    semantic similarity (sentence-transformers, when available)
  + keyword overlap
  + category match
  + community rating
  + experience

It is deliberately resilient: if the embedding model cannot be loaded (offline
venue Wi-Fi, missing torch, disabled via env) the ranker degrades to the
keyword/category/rating signals instead of crashing the API.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

CATEGORY_KEYWORDS = {
    "Health": {
        "doctor",
        "health",
        "medical",
        "medicine",
        "symptom",
        "pain",
        "fever",
        "sick",
        "illness",
        "disease",
        "hospital",
        "clinic",
        "mental",
        "anxiety",
        "anxious",
        "depression",
        "stress",
        "insomnia",
        "waking",
        "therapy",
        "therapist",
        "counsel",
        "counselling",
        "sleep",
    },
    "Career": {
        "career",
        "job",
        "resume",
        "cv",
        "interview",
        "internship",
        "salary",
        "promotion",
        "work",
        "office",
        "boss",
        "manager",
        "switch",
        "hiring",
        "placement",
        "linkedin",
    },
    "Fitness": {
        "fitness",
        "gym",
        "workout",
        "exercise",
        "weight",
        "muscle",
        "diet",
        "nutrition",
        "run",
        "running",
        "yoga",
        "training",
        "body",
        "fat",
        "strength",
        "cardio",
    },
    "Beauty": {
        "hair",
        "haircut",
        "hairstyle",
        "beauty",
        "skin",
        "makeup",
        "fashion",
        "style",
        "styling",
        "salon",
        "grooming",
        "outfit",
        "beard",
    },
    "Education": {
        "study",
        "exam",
        "school",
        "college",
        "university",
        "course",
        "learn",
        "learning",
        "tutor",
        "admission",
        "scholarship",
        "degree",
        "syllabus",
        "math",
        "science",
    },
    "Finance": {
        "money",
        "finance",
        "financial",
        "invest",
        "investing",
        "invested",
        "investor",
        "stock",
        "saving",
        "savings",
        "tax",
        "loan",
        "budget",
        "debt",
        "bank",
        "mutual",
        "insurance",
        "salary",
        "expense",
        "expenses",
    },
    "Legal": {
        "legal",
        "law",
        "lawyer",
        "court",
        "contract",
        "legal",
        "rights",
        "police",
        "fir",
        "property",
        "tenant",
        "landlord",
        "divorce",
    },
    "Technology": {
        "code",
        "coding",
        "programming",
        "programmer",
        "software",
        "developer",
        "development",
        "web",
        "html",
        "css",
        "react",
        "node",
        "frontend",
        "backend",
        "fullstack",
        "app",
        "website",
        "data",
        "ai",
        "machine",
        "python",
        "javascript",
        "cloud",
        "cyber",
        "security",
    },
    "Wellness": {
        "wellness",
        "meditation",
        "mindfulness",
        "habit",
        "lifestyle",
        "balance",
        "burnout",
        "motivation",
        "confidence",
        "relationship",
        "family",
        "life",
    },
}

STOPWORDS = {
    "a",
    "about",
    "am",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "get",
    "had",
    "has",
    "have",
    "he",
    "help",
    "her",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "need",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "so",
    "some",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
}

_CATEGORY_LOOKUP = {}
for _category, _words in CATEGORY_KEYWORDS.items():
    for _word in _words:
        _CATEGORY_LOOKUP.setdefault(_word, _category)

# Multi-word cues are stronger than a single token (e.g. "burnt out" is a
# wellness signal even though the sentence also contains "work").
PHRASE_KEYWORDS = {
    "burnt out": "Wellness",
    "burn out": "Wellness",
    "burnout": "Wellness",
    "can't sleep": "Wellness",
    "cannot sleep": "Wellness",
    "cant sleep": "Wellness",
    "not sleeping": "Wellness",
    "overwhelmed": "Wellness",
    "exhausted": "Wellness",
    "mental health": "Health",
    "chest pain": "Health",
    "panic attack": "Health",
    "job interview": "Career",
    "career change": "Career",
    "switch careers": "Career",
    "hair cut": "Beauty",
    "skin care": "Beauty",
    "hair fall": "Beauty",
    "break out": "Beauty",
    "lose weight": "Fitness",
    "build muscle": "Fitness",
    "workout plan": "Fitness",
    "credit card": "Finance",
    "mutual fund": "Finance",
    "savings account": "Finance",
    "study abroad": "Education",
    "entrance exam": "Education",
    "start investing": "Finance",
    "investing on": "Finance",
    "save money": "Finance",
    "work interview": "Career",
    "career guidance": "Career",
    "web development": "Technology",
    "full stack": "Technology",
    "learn to code": "Technology",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z+#.-]{2,}", (text or "").lower())
        if token not in STOPWORDS
    }


def detect_category(text: str) -> str | None:
    """Return the category whose vocabulary best matches ``text``."""
    lowered = (text or "").lower()
    tokens = tokenize(lowered)
    if not tokens and not lowered:
        return None

    scores: dict[str, int] = {}
    for phrase, category in PHRASE_KEYWORDS.items():
        if phrase in lowered:
            scores[category] = scores.get(category, 0) + 3

    for token in tokens:
        category = _CATEGORY_LOOKUP.get(token)
        if category:
            scores[category] = scores.get(category, 0) + 1

    if not scores:
        return None

    return max(scores, key=scores.get)


@lru_cache(maxsize=1)
def _load_embedder():
    """Load the sentence-transformer once, or return ``None`` if unavailable."""
    if os.environ.get("GUIDEME_DISABLE_EMBEDDINGS", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return None

    try:
        from sentence_transformers import SentenceTransformer, util

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model, util
    except Exception:  # pragma: no cover - depends on the venue environment
        return None


def semantic_available() -> bool:
    """True when the embedding model can be used for hybrid ranking."""
    return _load_embedder() is not None


def _expert_text(expert) -> str:
    """A natural-language profile works far better with sentence embeddings
    than a bag of keywords."""
    name = getattr(expert, "name", "") or "This expert"
    profession = getattr(expert, "profession", "") or "consultant"
    category = getattr(expert, "category", "") or "general"
    experience = getattr(expert, "experience", 0) or 0
    bio = (getattr(expert, "bio", "") or "").strip()
    languages = getattr(expert, "languages", "") or ""
    availability = getattr(expert, "availability", "") or ""

    parts = [
        f"{name} is a {profession} in the {category} category with {experience} years of experience."
    ]
    if bio:
        parts.append(bio)
    if languages:
        parts.append(f"Speaks {languages}.")
    if availability:
        parts.append(f"Available {availability}.")
    text = " ".join(parts)
    return re.sub(r"\s+", " ", text).strip()


def _rating(expert):
    """Prefer the annotated average to avoid an N+1 query."""
    if hasattr(expert, "avg_rating"):
        value = expert.avg_rating
        return round(value, 1) if value is not None else None
    return expert.rating


def _review_count(expert):
    if hasattr(expert, "total_reviews"):
        return expert.total_reviews
    return expert.review_count


def _semantic_scores(question: str, experts: list) -> list[float] | None:
    loaded = _load_embedder()
    if loaded is None:
        return None

    model, util = loaded
    try:
        question_embedding = model.encode(question, convert_to_tensor=True)
        expert_embeddings = model.encode(
            [_expert_text(expert) for expert in experts], convert_to_tensor=True
        )
        similarities = util.cos_sim(question_embedding, expert_embeddings)[0]
        return [float(score) for score in similarities]
    except Exception:  # pragma: no cover - defensive
        return None


def _reason(expert, category_match: bool, matched_keywords: set[str]) -> str:
    bits = [expert.profession]
    if category_match and expert.category:
        bits.append(f"{expert.category} specialist")
    if expert.experience:
        bits.append(f"{expert.experience} yrs experience")
    rating = _rating(expert)
    if rating is not None:
        bits.append(f"rated {rating}/5 from {_review_count(expert)} review(s)")
    if matched_keywords:
        bits.append("matches " + ", ".join(sorted(matched_keywords)[:3]))
    if expert.languages:
        bits.append(f"speaks {expert.languages}")
    return " · ".join(bits)


def rank_experts(question: str, experts, category: str | None = None) -> list[dict]:
    """Rank ``experts`` for ``question`` and return match metadata.

    Each item is ``{"expert": Expert, "score": float, "reason": str,
    "matched": [...]}`` where ``score`` is 0-100.
    """
    experts = list(experts)
    if not experts:
        return []

    question = (question or "").strip()
    question_tokens = tokenize(question)
    detected_category = category or detect_category(question)

    semantic = _semantic_scores(question, experts) if question else None
    has_semantic = semantic is not None

    results = []
    for index, expert in enumerate(experts):
        expert_tokens = tokenize(_expert_text(expert))
        matched = question_tokens & expert_tokens

        keyword_score = 0.0
        if question_tokens:
            keyword_score = len(matched) / len(question_tokens)

        category_match = bool(
            detected_category
            and (
                (expert.category or "").lower() == detected_category.lower()
                or detected_category.lower() in (expert.profession or "").lower()
            )
        )

        rating = _rating(expert)
        rating_score = (rating / 5.0) if rating is not None else 0.6
        experience_score = min(expert.experience or 0, 15) / 15.0

        if has_semantic:
            # MiniLM cosine scores for short query/profile pairs sit in a low
            # band (~0.05–0.45), so calibrate before blending. The rank order is
            # unchanged; this only makes the displayed 0–100 score meaningful.
            semantic_score = max(0.0, min(1.0, semantic[index] / 0.45))
            total = (
                0.45 * semantic_score
                + 0.25 * keyword_score
                + 0.15 * (1.0 if category_match else 0.0)
                + 0.10 * rating_score
                + 0.05 * experience_score
            )
        else:
            total = (
                0.50 * keyword_score
                + 0.20 * (1.0 if category_match else 0.0)
                + 0.20 * rating_score
                + 0.10 * experience_score
            )

        results.append(
            {
                "expert": expert,
                "score": 0,
                "_raw": total,
                "reason": _reason(expert, category_match, matched),
                "matched": sorted(matched)[:5],
            }
        )

    # Calibrate 0–1 relevance into a readable 0–100 confidence. The top result
    # is scaled by how strong the absolute best match is, so an unrelated query
    # still produces low scores instead of a misleading 99%.
    best = max(item["_raw"] for item in results)
    for item in results:
        relative = (item["_raw"] / best) if best else 0.0
        confidence = min(1.0, best / 0.45)
        item["score"] = int(
            round(92 * (relative ** 0.75) * max(0.35, confidence))
        )
        del item["_raw"]

    results.sort(
        key=lambda item: (item["score"], _rating(item["expert"]) or 0), reverse=True
    )
    return results


def recommend_experts(question, experts, category=None, limit=5):
    """Backwards-compatible helper returning only Expert instances."""
    ranked = rank_experts(question, experts, category=category)
    return [item["expert"] for item in ranked[:limit]]
