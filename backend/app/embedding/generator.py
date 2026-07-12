import logging
import numpy as np
import hashlib
from typing import List
from app.config.config import settings

logger = logging.getLogger(__name__)

# Global model instance
_model = None

def get_embedding_model():
    global _model
    if _model is not None:
        return _model
        
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading SentenceTransformer model: {settings.EMBEDDING_MODEL_NAME}...")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        logger.info("SentenceTransformer model loaded successfully.")
    except Exception as e:
        logger.warning(f"Failed to load SentenceTransformer ({str(e)}). Using deterministic fallback embedding generator.")
        _model = FallbackEmbeddingGenerator(dimension=384)
    return _model

class FallbackEmbeddingGenerator:
    """
    Deterministic fallback embedding generator that creates a 384-dimension vector
    using SHA-256 hash of the input text. Keeps vector search reproducible without downloads.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def encode(self, sentences: List[str] or str, show_progress_bar: bool = False) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
            
        embeddings = []
        for text in sentences:
            # Generate deterministic values using hashlib
            sha = hashlib.sha256(text.encode("utf-8")).digest()
            # Seed a random generator with the hash
            seed = int.from_bytes(sha, "big") % (2**32 - 1)
            rng = np.random.default_rng(seed)
            # Create a unit vector of dimension 384
            vec = rng.normal(0, 1.0, self.dimension)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec)
            
        return np.array(embeddings, dtype=np.float32)

class EmbeddingService:
    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        model = get_embedding_model()
        vector = model.encode(text)
        # If it returns a 2D array for a single string, flatten it
        if len(vector.shape) > 1:
            vector = vector[0]
        return vector.tolist()

    @classmethod
    def get_embeddings(cls, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = get_embedding_model()
        vectors = model.encode(texts)
        return vectors.tolist()
