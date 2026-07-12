#!/usr/bin/env python3
"""
Module 4 & 5: Embeddings & Candidate Matching (Incremental + Per-Obligation Top-K)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
JSON_DIR = Path("extracted_json")
OUTPUT_DIR = Path("output")
EMBEDDINGS_CACHE_FILE = Path("embeddings.npz")
REGISTRY_FILE = Path(".embedding_registry.json")  # Tracks which JSONs are embedded
TOP_K_DEFAULT = 15
SIMILARITY_THRESHOLD_DEFAULT = 0.4

OUTPUT_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("candidate_matcher")

_model: Optional[SentenceTransformer] = None
_embedding_registry: Optional[Dict] = None


def get_model() -> SentenceTransformer:
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully.")
    return _model


def load_obligations_from_json(json_dir: Path = JSON_DIR) -> List[Dict[str, Any]]:
    """Load all obligations from JSON files in the given directory."""
    all_obligations = []
    json_files = list(json_dir.glob("*.json"))

    if not json_files:
        logger.warning(f"No JSON files found in '{json_dir}'.")
        return []

    logger.info(f"Found {len(json_files)} JSON files in '{json_dir}'.")

    for json_path in json_files:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "obligations" in data:
            obligations = data["obligations"]
        elif isinstance(data, list):
            obligations = data
        else:
            logger.warning(f"Skipping {json_path.name}: Unexpected JSON structure.")
            continue

        policy_name = json_path.stem

        for idx, item in enumerate(obligations):
            normalized = {}

            if "obligation_id" in item:
                normalized["obligation_id"] = f"{policy_name}-{item['obligation_id']}"
            elif "id" in item:
                normalized["obligation_id"] = f"{policy_name}-{item['id']}"
            else:
                normalized["obligation_id"] = f"{policy_name}-{idx+1:03d}"

            if "text" in item:
                normalized["text"] = item["text"]
            elif "original_text" in item:
                normalized["text"] = item["original_text"]
            else:
                normalized["text"] = "No text available"

            normalized["topic"] = item.get("topic", "unknown")
            normalized["policy_id"] = policy_name

            # -------- Governance metadata --------
            normalized["policy_name"] = item.get("policy_name", policy_name)
            normalized["policy_version"] = item.get("policy_version", "")
            normalized["last_reviewed"] = item.get("last_reviewed", "")
            normalized["references"] = item.get("references", [])
            normalized["strength"] = item.get("strength", "")
            normalized["scope"] = item.get("scope", "")

            for key, value in item.items():
                if key not in ["id", "obligation_id", "text", "original_text", "topic"]:
                    normalized[key] = value

            all_obligations.append(normalized)

    logger.info(f"Loaded {len(all_obligations)} obligations total.")
    return all_obligations


def _load_registry() -> Dict:
    """Load the embedding registry from disk."""
    global _embedding_registry
    if _embedding_registry is not None:
        return _embedding_registry
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            _embedding_registry = json.load(f)
    else:
        _embedding_registry = {}
    return _embedding_registry


def _save_registry(registry: Dict):
    """Save the embedding registry atomically."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=".") as tmp:
        json.dump(registry, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, REGISTRY_FILE)
    logger.info(f"Registry saved to {REGISTRY_FILE}")


def get_files_to_process(json_dir: Path = JSON_DIR) -> Tuple[List[Path], List[Dict]]:
    """Compare JSON file modification times against the registry."""
    registry = _load_registry()
    files_to_process = []

    for json_path in json_dir.glob("*.json"):
        current_mtime = os.path.getmtime(json_path)
        policy_name = json_path.stem

        if policy_name in registry:
            if registry[policy_name]["mtime"] == current_mtime:
                logger.debug(f"Skipping {json_path.name} (unchanged).")
                continue
            else:
                logger.info(f"{json_path.name} modified. Re-processing.")

        files_to_process.append(json_path)

    all_obligations = load_obligations_from_json(json_dir)
    return files_to_process, all_obligations


def generate_incremental_embeddings(
    json_dir: Path = JSON_DIR,
    cache_file: Path = EMBEDDINGS_CACHE_FILE,
) -> int:
    """Generates embeddings only for newly added/modified JSON files."""
    logger.info("=" * 60)
    logger.info("STARTING INCREMENTAL EMBEDDING GENERATION")
    logger.info("=" * 60)

    files_to_process, all_obligations = get_files_to_process(json_dir)

    if not files_to_process:
        logger.info("No new or modified JSON files. Skipping embedding generation.")
        return len(all_obligations)

    logger.info(f"Processing {len(files_to_process)} file(s): {[f.name for f in files_to_process]}")

    existing_ids = []
    existing_embeddings = []
    if cache_file.exists():
        data = np.load(cache_file, allow_pickle=True)
        existing_ids = data["ids"].tolist()
        existing_embeddings = data["embeddings"]
        logger.info(f"Loaded existing cache: {len(existing_ids)} embeddings.")

    model = get_model()
    new_obligations = []

    for json_path in files_to_process:
        policy_name = json_path.stem
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "obligations" in data:
            obligations = data["obligations"]
        elif isinstance(data, list):
            obligations = data
        else:
            logger.warning(f"Skipping {json_path.name}: Unexpected structure.")
            continue

        for idx, item in enumerate(obligations):
            if "obligation_id" in item:
                oid = f"{policy_name}-{item['obligation_id']}"
            elif "id" in item:
                oid = f"{policy_name}-{item['id']}"
            else:
                oid = f"{policy_name}-{idx+1:03d}"

            text = item.get("text") or item.get("original_text") or "No text available"

            embedding_text = f"""
                Topic: {item.get('topic','')}

                Strength: {item.get('strength','')}

                Scope: {item.get('scope','')}

                Reference: {' '.join(item.get('references',[]))}

                {text}
            """

            new_obligations.append({
                "id": oid,
                "text": embedding_text
            })

    if not new_obligations:
        logger.info("No new obligations found to embed.")
        return len(all_obligations)

    texts = [o["text"] for o in new_obligations]
    logger.info(f"Encoding {len(texts)} new texts...")
    new_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    all_ids = existing_ids + [o["id"] for o in new_obligations]
    all_embeddings = (
        np.vstack([existing_embeddings, new_embeddings])
        if len(existing_embeddings) > 0
        else new_embeddings
    )

    with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as tmp:
        np.savez_compressed(tmp, ids=all_ids, embeddings=all_embeddings)
        tmp_path = tmp.name
    os.replace(tmp_path, cache_file)
    logger.info(f"Saved {len(all_ids)} embeddings to {cache_file}")

    registry = _load_registry()
    for json_path in files_to_process:
        policy_name = json_path.stem
        registry[policy_name] = {
            "mtime": os.path.getmtime(json_path),
            "updated_at": datetime.now().isoformat(),
        }
    _save_registry(registry)

    logger.info(f"Incremental embedding complete. Total obligations: {len(all_ids)}")
    return len(all_ids)


# ------------------------------------------------------------------
# ADMINISTRATIVE / BOILERPLATE FILTERING
# ------------------------------------------------------------------
AUTO_REDUNDANT_THRESHOLD = 0.98   # near-identical wording -> safe to auto-resolve
NEAR_DUPLICATE_THRESHOLD = 0.999   # essentially the same string, regardless of topic

ADMINISTRATIVE_TOPIC_KEYWORDS = [
    "training",
    "review",
    "maintenance",
    "governance",
    "applicability",
    "scope",
    "exception",
    "non-compliance",
    "noncompliance",
    "enforcement",
]


def is_administrative_topic(topic: str) -> bool:
    """Return True if a topic string looks like policy 'furniture' rather
    than a substantive security control (password, MFA, encryption, etc.)."""
    if not topic:
        return False
    topic_lower = topic.lower()
    if topic_lower.startswith("policy"):
        return True
    return any(keyword in topic_lower for keyword in ADMINISTRATIVE_TOPIC_KEYWORDS)


def classify_pair_auto(score, topic_a, topic_b):

    if score >= NEAR_DUPLICATE_THRESHOLD:
        return "REDUNDANT_AUTO"

    if (
        score >= AUTO_REDUNDANT_THRESHOLD
        and
        topic_a.lower() == topic_b.lower()
    ):
        return "REDUNDANT_AUTO"

    if (
        score >= AUTO_REDUNDANT_THRESHOLD
        and
        (
            is_administrative_topic(topic_a)
            or
            is_administrative_topic(topic_b)
        )
    ):
        return "REDUNDANT_AUTO"

    return None

def same_policy(ob_a, ob_b):
    return ob_a["policy_id"] == ob_b["policy_id"]


def same_text(ob_a, ob_b):
    return (
        ob_a.get("text", "").strip().lower()
        ==
        ob_b.get("text", "").strip().lower()
    )


def same_topic(ob_a, ob_b):
    return (
        ob_a.get("topic", "").strip().lower()
        ==
        ob_b.get("topic", "").strip().lower()
    )

def build_candidate_map(
    threshold: float = SIMILARITY_THRESHOLD_DEFAULT,
    top_k: int = TOP_K_DEFAULT,
    json_dir: Path = JSON_DIR,
    cache_file: Path = EMBEDDINGS_CACHE_FILE,
) -> Dict[str, Any]:
    """
    Generate per-obligation top-k candidates.
    Returns a dict with:
      - "candidate_map": { obligation_id: {source_text, source_topic, neighbors: [...] } }
      - "flat_pairs": all candidate pairs, with auto_classification/needs_llm_review
      - "auto_resolved_pairs": pairs safely resolved without an LLM call (kept, not discarded)
      - "pairs_for_llm_review": pairs Module 6 should actually reason over
      - "metadata": counts + threshold/top_k used
    """
    logger.info("=" * 60)
    logger.info("STARTING CANDIDATE MAP GENERATION (Per-Obligation Top-K)")
    logger.info("=" * 60)

    generate_incremental_embeddings(json_dir, cache_file)

    obligations = load_obligations_from_json(json_dir)
    if not obligations:
        logger.warning("No obligations loaded. Returning empty.")
        return {"candidate_map": {}, "flat_pairs": [], "auto_resolved_pairs": [],
                "pairs_for_llm_review": [], "metadata": {"total": 0, "threshold": threshold, "top_k": top_k}}

    if not cache_file.exists():
        logger.error(f"Embeddings cache {cache_file} not found despite generation attempt.")
        return {"candidate_map": {}, "flat_pairs": [], "auto_resolved_pairs": [],
                "pairs_for_llm_review": [], "metadata": {"total": len(obligations), "threshold": threshold, "top_k": top_k}}

    data = np.load(cache_file, allow_pickle=True)
    cached_ids = data["ids"].tolist()
    embeddings = data["embeddings"]

    id_to_index = {oid: i for i, oid in enumerate(cached_ids)}
    valid_obligations = []
    valid_indices = []
    for ob in obligations:
        oid = ob["obligation_id"]
        if oid in id_to_index:
            valid_obligations.append(ob)
            valid_indices.append(id_to_index[oid])
        else:
            logger.warning(f"Obligation {oid} not found in embeddings cache. Skipping.")

    if len(valid_obligations) < 2:
        logger.warning("Less than 2 valid obligations. Skipping candidate generation.")
        return {"candidate_map": {}, "flat_pairs": [], "auto_resolved_pairs": [],
                "pairs_for_llm_review": [], "metadata": {"total": len(valid_obligations), "threshold": threshold, "top_k": top_k}}

    valid_embeddings = embeddings[valid_indices]
    logger.info(f"Computing similarity matrix for {len(valid_obligations)} obligations...")

    sim_matrix = cos_sim(valid_embeddings, valid_embeddings).numpy()

    candidate_map = {}
    flat_pairs = []
    seen_pairs = set()

    for i, ob_i in enumerate(valid_obligations):
        oid_i = ob_i["obligation_id"]
        source_text = ob_i.get("text", "")
        source_topic = ob_i.get("topic", "unknown")
        scores = sim_matrix[i]
        sorted_indices = np.argsort(scores)[::-1]

        neighbors = []
        count = 0
        for j in sorted_indices:

            if i == j:
                continue

            if scores[j] < threshold:
                break

            ob_j = valid_obligations[j]

            # Ignore obligations from the SAME policy
            if same_policy(ob_i, ob_j):
                continue

            # Ignore EXACT duplicate sentences
            if same_text(ob_i, ob_j):
                continue

            # Ignore almost identical embeddings
            if scores[j] >= 0.995:
                continue
            oid_j = ob_j["obligation_id"]

            pair_key = tuple(sorted([oid_i, oid_j]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                topic_a = ob_i.get("topic", "unknown")
                topic_b = ob_j.get("topic", "unknown")
                score = float(scores[j])
                auto_class = classify_pair_auto(score, topic_a, topic_b)

                flat_pairs.append({
                    "obligation_a_id": oid_i,
                    "obligation_b_id": oid_j,
                    "similarity": score,
                    "policy_a": ob_i["policy_name"],
                    "policy_b": ob_j["policy_name"],
                    "topic_a": topic_a,
                    "topic_b": topic_b,
                    "text_a": ob_i["text"],
                    "text_b": ob_j["text"],
                    "strength_a": ob_i.get("strength", ""),
                    "strength_b": ob_j.get("strength", ""),
                    "scope_a": ob_i.get("scope", ""),
                    "scope_b": ob_j.get("scope", ""),
                    "policy_version_a": ob_i.get("policy_version", ""),
                    "policy_version_b": ob_j.get("policy_version", ""),
                    "last_reviewed_a": ob_i.get("last_reviewed", ""),
                    "last_reviewed_b": ob_j.get("last_reviewed", ""),
                    "references_a": ob_i.get("references", []),
                    "references_b": ob_j.get("references", []),
                    "auto_classification": auto_class,
                    "needs_llm_review": auto_class is None,
                })

            neighbors.append({
                "neighbor_id": oid_j,
                "score": float(scores[j]),
                "text": ob_j.get("text", ""),
                "topic": ob_j.get("topic", "unknown"),
            })
            count += 1
            if count >= top_k:
                break

        candidate_map[oid_i] = {
            "policy_name": ob_i["policy_name"],
            "last_reviewed": ob_i.get("last_reviewed", ""),
            "policy_version": ob_i.get("policy_version", ""),
            "references": ob_i.get("references", []),
            "strength": ob_i.get("strength", ""),
            "source_text": source_text,
            "source_topic": source_topic,
            "neighbors": neighbors,
        }

    flat_pairs.sort(key=lambda x: x["similarity"], reverse=True)

    auto_resolved_pairs = [p for p in flat_pairs if not p["needs_llm_review"]]
    pairs_for_llm_review = [p for p in flat_pairs if p["needs_llm_review"]]

    result = {
        "candidate_map": candidate_map,
        "flat_pairs": flat_pairs,
        "auto_resolved_pairs": auto_resolved_pairs,
        "pairs_for_llm_review": pairs_for_llm_review,
        "metadata": {
            "total_obligations": len(valid_obligations),
            "total_pairs": len(flat_pairs),
            "auto_resolved_count": len(auto_resolved_pairs),
            "pairs_for_llm_review_count": len(pairs_for_llm_review),
            "threshold": threshold,
            "top_k": top_k,
            "generated_at": datetime.now().isoformat(),
        },
    }

    output_file = OUTPUT_DIR / "candidate_pairs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved candidate map to {output_file}")
    logger.info(f"   Total obligations: {len(valid_obligations)}")
    logger.info(f"   Total unique pairs: {len(flat_pairs)}")
    logger.info(f"   Auto-resolved: {len(auto_resolved_pairs)} | For LLM review: {len(pairs_for_llm_review)}")
    return result

if __name__ == "__main__":
    # Test script run
    print("Candidate service initialized and ready.")
