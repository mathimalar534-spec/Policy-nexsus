# predict_pairs.py - Execute ML classifier predictions on obligation pairs for the Node.js backend

import os
import sys
import json
import numpy as np
import joblib

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

def predict():
    try:
        # Load stdin input
        input_data = json.loads(sys.stdin.read())
        pairs = input_data.get("pairs", [])
        
        if not pairs:
            print(json.dumps([]))
            return
            
        # 1. Load trained classifier
        model_path = os.path.join(os.path.dirname(__file__), "backend", "app", "conflict_engine", "conflict_classifier.joblib")
        if not os.path.exists(model_path):
            # Fallback relative search
            model_path = "backend/app/conflict_engine/conflict_classifier.joblib"
            
        clf = joblib.load(model_path)
        
        # 2. Generate embeddings
        from app.embedding.generator import EmbeddingService
        
        texts = []
        for p in pairs:
            texts.append(p["a"])
            texts.append(p["b"])
            
        # Bulk encode to optimize speed
        all_embs = np.array(EmbeddingService.get_embeddings(texts))
        
        results = []
        import re
        topics_vocab = ["physical", "patch", "retention", "provisioning", "third-party", "hr", "mobile", "api", "monitoring", "password", "logging", "vendor", "endpoint", "change", "encryption", "backup"]
        negations = ["not", "prohibit", "forbidden", "shall not", "must not", "never", "prohibited", "cannot"]

        for idx in range(len(pairs)):
            # Retrieve embeddings for the pair
            emb_a = all_embs[2 * idx]
            emb_b = all_embs[2 * idx + 1]
            
            text_a = pairs[idx]["a"]
            text_b = pairs[idx]["b"]
            
            # Compute features
            sim = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-8)
            abs_diff = np.abs(emb_a - emb_b)
            prod = emb_a * emb_b
            
            text_a_low = text_a.lower()
            text_b_low = text_b.lower()
            
            words_a = set(re.findall(r'\w+', text_a_low))
            words_b = set(re.findall(r'\w+', text_b_low))
            overlap = len(words_a.intersection(words_b)) / max(len(words_a), len(words_b), 1)
            
            has_neg_a = 1 if any(n in text_a_low for n in negations) else 0
            has_neg_b = 1 if any(n in text_b_low for n in negations) else 0
            neg_mismatch = 1 if has_neg_a != has_neg_b else 0
            
            topic_a = next((t for t in topics_vocab if t in text_a_low), "general")
            topic_b = next((t for t in topics_vocab if t in text_b_low), "general")
            topic_match = 1 if (topic_a == topic_b and topic_a != "general") else 0
            
            features = np.hstack(([sim], abs_diff, prod, [overlap, neg_mismatch, topic_match])).reshape(1, -1)
            
            # Predict
            pred = clf.predict(features)[0]
            prob = float(np.max(clf.predict_proba(features)))
            
            results.append({
                "label": pred,
                "confidence": prob
            })
            
        print(json.dumps(results))
    except Exception as e:
        # Return error array
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    predict()
