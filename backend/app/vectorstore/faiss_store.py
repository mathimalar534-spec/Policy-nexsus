import os
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Any
from app.config.config import settings

logger = logging.getLogger(__name__)

class FAISSStore:
    def __init__(self, index_path: str = settings.FAISS_INDEX_PATH, dimension: int = 384):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.id_to_index = {}  # Map database obligation_id to index position (for pure python fallback)
        self.index_to_id = {}  # Map index position to database obligation_id
        self.use_faiss = True
        
        # Initialize
        self._init_index()

    def _init_index(self):
        try:
            import faiss
            # L2 normalized vectors searched with Inner Product = Cosine Similarity
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(quantizer)
            logger.info("FAISS Index initialized successfully using IndexIDMap.")
        except Exception as e:
            logger.warning(f"Could not import/initialize FAISS ({str(e)}). Falling back to pure NumPy vector store.")
            self.use_faiss = False
            self.vectors = []
            self.obligation_ids = []

    def add_vectors(self, obligation_ids: List[int], vectors: List[List[float]]):
        if not vectors or not obligation_ids:
            return
            
        np_vectors = np.array(vectors, dtype=np.float32)
        # Normalize vectors for cosine similarity (inner product)
        norms = np.linalg.norm(np_vectors, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        np_vectors = np_vectors / norms

        if self.use_faiss:
            ids = np.array(obligation_ids, dtype=np.int64)
            self.index.add_with_ids(np_vectors, ids)
        else:
            for ob_id, vec in zip(obligation_ids, np_vectors.tolist()):
                if ob_id in self.id_to_index:
                    # Update
                    idx = self.id_to_index[ob_id]
                    self.vectors[idx] = vec
                else:
                    # Append
                    self.id_to_index[ob_id] = len(self.vectors)
                    self.index_to_id[len(self.vectors)] = ob_id
                    self.vectors.append(vec)
                    self.obligation_ids.append(ob_id)

    def search(self, query_vector: List[float], k: int = 5) -> List[Tuple[int, float]]:
        """
        Query FAISS index for top K similar obligations.
        Returns: List of (obligation_id, similarity_score)
        """
        if self.use_faiss:
            if self.index is None or self.index.ntotal == 0:
                return []
                
            np_query = np.array([query_vector], dtype=np.float32)
            # Normalize query
            norm = np.linalg.norm(np_query)
            if norm > 0:
                np_query = np_query / norm
                
            k = min(k, self.index.ntotal)
            similarities, ids = self.index.search(np_query, k)
            
            results = []
            for sim, ob_id in zip(similarities[0], ids[0]):
                if ob_id != -1:
                    results.append((int(ob_id), float(sim)))
            return results
        else:
            # NumPy Cosine Similarity fallback
            if not self.vectors:
                return []
                
            np_query = np.array(query_vector, dtype=np.float32)
            norm = np.linalg.norm(np_query)
            if norm > 0:
                np_query = np_query / norm
                
            np_vectors = np.array(self.vectors, dtype=np.float32)
            # Query is 1D, vectors is 2D -> dot product is shape (N,)
            similarities = np.dot(np_vectors, np_query)
            
            # Get top K indices
            top_k_indices = np.argsort(similarities)[::-1][:k]
            
            results = []
            for idx in top_k_indices:
                ob_id = self.obligation_ids[idx]
                results.append((int(ob_id), float(similarities[idx])))
            return results

    def save(self):
        os.makedirs(self.index_path, exist_ok=True)
        if self.use_faiss:
            try:
                import faiss
                faiss.write_index(self.index, os.path.join(self.index_path, "index.faiss"))
                logger.info("FAISS index saved successfully.")
            except Exception as e:
                logger.error(f"Error saving FAISS index: {str(e)}")
        else:
            # Save NumPy vectors
            data = {
                "obligation_ids": self.obligation_ids,
                "vectors": self.vectors
            }
            try:
                with open(os.path.join(self.index_path, "vectors.json"), "w") as f:
                    json.dump(data, f)
                logger.info("NumPy vectors saved successfully.")
            except Exception as e:
                logger.error(f"Error saving NumPy vectors: {str(e)}")

    def load(self):
        if self.use_faiss:
            index_file = os.path.join(self.index_path, "index.faiss")
            if os.path.exists(index_file):
                try:
                    import faiss
                    self.index = faiss.read_index(index_file)
                    logger.info("FAISS index loaded successfully.")
                except Exception as e:
                    logger.error(f"Error loading FAISS index: {str(e)}. Reinitializing index.")
                    self._init_index()
        else:
            vectors_file = os.path.join(self.index_path, "vectors.json")
            if os.path.exists(vectors_file):
                try:
                    with open(vectors_file, "r") as f:
                        data = json.load(f)
                    self.obligation_ids = data["obligation_ids"]
                    self.vectors = data["vectors"]
                    self.id_to_index = {ob_id: i for i, ob_id in enumerate(self.obligation_ids)}
                    self.index_to_id = {i: ob_id for i, ob_id in enumerate(self.obligation_ids)}
                    logger.info("NumPy vectors loaded successfully.")
                except Exception as e:
                    logger.error(f"Error loading NumPy vectors: {str(e)}")

    def clear(self):
        self._init_index()
        if not self.use_faiss:
            self.vectors = []
            self.obligation_ids = []
            self.id_to_index = {}
            self.index_to_id = {}
        
        # Remove saved files
        for f in ["index.faiss", "vectors.json"]:
            path = os.path.join(self.index_path, f)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

# Singleton instance of vector store
vector_store = FAISSStore()
