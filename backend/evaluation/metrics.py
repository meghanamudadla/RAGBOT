import hashlib
from typing import List, Tuple

def get_text_fingerprint(text: str) -> str:
    """Stable chunk identification via SHA-256 fingerprint."""
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()

def calculate_precision_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0 # Mathematically 0 if no relevant exist, excluded usually
    retrieved_k = retrieved_ids[:k]
    hits = sum(1 for cid in retrieved_k if cid in relevant_ids)
    return hits / k

def calculate_recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    hits = sum(1 for cid in retrieved_k if cid in relevant_ids)
    return hits / len(relevant_ids)

def calculate_hit_rate_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    hits = sum(1 for cid in retrieved_k if cid in relevant_ids)
    return 1.0 if hits > 0 else 0.0

def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    for i, cid in enumerate(retrieved_ids[:k]):
        if cid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0

def get_groundedness_rates(overall_confidence: str) -> Tuple[int, int]:
    """
    Mapping used: Grounded = High, Partially grounded = Medium, Ungrounded = Low.
    Returns (strict_rate_int, lenient_rate_int) where values are 0 or 1.
    Strict = High only. Lenient = High + Medium.
    """
    conf = (overall_confidence or "").lower()
    is_strict = 1 if conf == "high" else 0
    is_lenient = 1 if conf in ["high", "medium"] else 0
    return is_strict, is_lenient

def calculate_mean(data: List[float]) -> float:
    if not data:
        return 0.0
    return sum(data) / len(data)

def calculate_percentile(data: List[float], percentile: float) -> float:
    if not data:
        return 0.0
    s_data = sorted(data)
    idx = (len(s_data) - 1) * percentile
    if int(idx) == idx:
        return s_data[int(idx)]
    i = int(idx)
    return s_data[i] + (idx - i) * (s_data[i + 1] - s_data[i])

# --- Unit Tests ---
def run_unit_tests():
    # test precision
    assert calculate_precision_at_k(["A", "B", "C"], ["A", "D"], 3) == 1/3
    assert calculate_precision_at_k(["A", "C"], ["A", "B", "C"], 2) == 2/2
    # test recall
    assert calculate_recall_at_k(["A", "B", "C"], ["A", "D"], 3) == 1/2
    # test hit rate
    assert calculate_hit_rate_at_k(["A", "B", "C"], ["D", "E"], 3) == 0.0
    assert calculate_hit_rate_at_k(["A", "B", "C"], ["B", "E"], 3) == 1.0
    # test mrr
    assert calculate_mrr(["C", "B", "A"], ["A"], 5) == 1/3
    assert calculate_mrr(["A", "B", "C"], ["C", "A"], 5) == 1/1
    # test percentile
    arr = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert calculate_percentile(arr, 0.5) == 3.0
    assert calculate_percentile(arr, 0.95) == 4.8
    # check rates
    assert get_groundedness_rates("high") == (1, 1)
    assert get_groundedness_rates("medium") == (0, 1)
    assert get_groundedness_rates("low") == (0, 0)
    print("All metric unit tests passed.")

if __name__ == "__main__":
    run_unit_tests()
