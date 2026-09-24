"""
Groundedness checking for RAG responses.

Uses a cross-encoder NLI model to verify that each claim in the answer
is supported by the cited source chunks. Runs locally with no LLM API calls.
"""
import re
from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache(maxsize=1)
def _load_groundedness_model():
    """Load cross-encoder NLI model once and cache for process lifetime."""
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.GROUNDEDNESS_MODEL_NAME, device="cpu")


def get_groundedness_model():
    """Public accessor for the groundedness cross-encoder model."""
    return _load_groundedness_model()


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using a simple regex.
    Handles common sentence endings and avoids splitting on abbreviations.
    """
    if not text.strip():
        return []
    
    # Simple regex-based sentence splitter
    # Matches sentence endings (.!?) followed by whitespace and capital letter or end of string
    # Also handles colon-based connectives (e.g., "Here is a summary: Revenue increased.")
    # First, normalize by adding period after colon-connectives if followed by capital
    normalized = re.sub(r'(?<=:)\s+(?=[A-Z])', '. ', text.strip())
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', normalized)
    
    # Filter out very short fragments that are likely not real sentences
    return [s.strip() for s in sentences if len(s.strip()) >= 8]


def _extract_citation_ids(sentence: str) -> list[int]:
    """
    Extract citation numbers from a sentence.
    Handles formats like [1], [1, 2], [1,2,3], [ 1 , 2 , 3 ], etc.
    """
    # Find all bracketed numbers (allowing optional spaces)
    matches = re.findall(r'\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]', sentence)
    citation_ids = []
    for match in matches:
        # Split by comma and convert to int
        ids = [int(x.strip()) for x in match.split(',')]
        citation_ids.extend(ids)
    return citation_ids


def _is_connective_sentence(sentence: str) -> bool:
    """
    Heuristic to detect connective/filler sentences that don't make factual claims.
    Examples: "Here is a summary:", "In conclusion:", "To summarize:"
    """
    s = sentence.strip().lower()
    # Short sentences with colons are often connectives
    if len(s) < 50 and s.endswith(':'):
        return True
    # Common connective phrases
    connective_starts = [
        'here is', 'here are', 'in summary', 'to summarize', 
        'in conclusion', 'overall', 'finally', 'note that',
        'please note', 'note:', 'summary:'
    ]
    for start in connective_starts:
        if s.startswith(start):
            return True
    return False


def check_groundedness(answer_text: str, hits: list[dict]) -> dict:
    """
    Check how well each sentence in the answer is supported by cited chunks.
    
    Args:
        answer_text: The generated answer text.
        hits: List of retrieved chunks with 'id', 'document', 'metadata'.
        
    Returns:
        Dict with overall_confidence and per-sentence analysis.
    """
    if not answer_text.strip() or not hits:
        return {
            "overall_confidence": "low",
            "sentences": []
        }
    
    # Build lookup: citation number (1-indexed) -> chunk text
    # hits order matches citation numbers in the prompt
    cited_chunks = {}
    for idx, hit in enumerate(hits, 1):
        cited_chunks[idx] = hit.get("document", "")
    
    sentences = _split_sentences(answer_text)
    if not sentences:
        return {
            "overall_confidence": "low",
            "sentences": []
        }
    
    model = get_groundedness_model()
    results = []
    grounded_count = 0
    scored_count = 0
    
    for sentence in sentences:
        citation_ids = _extract_citation_ids(sentence)
        
        # Skip connective/filler sentences
        if not citation_ids:
            if _is_connective_sentence(sentence):
                results.append({
                    "text": sentence,
                    "citation_ids": [],
                    "status": "skipped",
                    "score": None
                })
                continue
            # Non-trivial sentence with no citations -> unsupported
            results.append({
                "text": sentence,
                "citation_ids": [],
                "status": "unsupported",
                "score": 0.0
            })
            continue
        
        # Score against each cited chunk
        max_score = 0.0
        for cid in citation_ids:
            chunk_text = cited_chunks.get(cid, "")
            if not chunk_text:
                continue
            # Cross-encoder predicts entailment/neutral/contradiction
            # For NLI models, we use the entailment probability
            try:
                scores = model.predict([(sentence, chunk_text)], show_progress_bar=False)
                # Model outputs logits for [contradiction, neutral, entailment] or similar
                # Take the entailment score (last index typically)
                entailment_score = float(scores[0][-1]) if len(scores[0]) >= 3 else float(scores[0][0])
                max_score = max(max_score, entailment_score)
            except Exception:
                # If model fails, treat as unsupported
                max_score = 0.0
        
        # Classify based on thresholds
        if max_score >= settings.GROUNDEDNESS_GROUNDED_THRESHOLD:
            status = "grounded"
            grounded_count += 1
        elif max_score >= settings.GROUNDEDNESS_WEAK_THRESHOLD:
            status = "weak"
        else:
            status = "unsupported"
        
        scored_count += 1
        results.append({
            "text": sentence,
            "citation_ids": citation_ids,
            "status": status,
            "score": round(max_score, 3)
        })
    
    # Determine overall confidence
    if scored_count == 0:
        overall = "low"
    else:
        grounded_ratio = grounded_count / scored_count
        if grounded_ratio >= settings.GROUNDEDNESS_HIGH_CONFIDENCE_RATIO:
            overall = "high"
        elif grounded_ratio >= settings.GROUNDEDNESS_LOW_CONFIDENCE_RATIO:
            overall = "medium"
        else:
            overall = "low"
    
    return {
        "overall_confidence": overall,
        "sentences": results
    }