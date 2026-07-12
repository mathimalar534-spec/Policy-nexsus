# train_classifier.py - Optimized classifier training with GRC data augmentation and local vectorization fallback

import os
import sys
import json
import numpy as np
import re
import random

# Resolve app module path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Import scikit-learn components
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import joblib

# 1. DATA AUGMENTATION - Generate synthetic GRC policy obligations to balance classes
def generate_augmented_dataset():
    augmented_data = []
    
    # Topic: password
    p_must = [
        "Passwords must contain at least 12 characters and undergo reset every 90 days.",
        "Corporate accounts shall enforce a minimum 14-character password length.",
        "User passwords must combine uppercase, lowercase, and numeric digits.",
        "Security credentials must be updated annually by all staff members."
    ]
    p_conflict = [
        "Password rotation is not required under any circumstances.",
        "Automatic password resets are prohibited; enforce MFA instead.",
        "Users are prohibited from updating passwords without administrator approval.",
        "Credentials shall never expire or require periodic rotation."
    ]
    p_redundant = [
        "All credentials must have at least 12 symbols and change quarterly.",
        "It is mandatory to use passwords with a minimum length of 14 characters.",
        "Passwords must be structured with caps, lowercases, and numbers.",
        "Staff are required to refresh their login passwords once per year."
    ]
    
    # Topic: logging
    l_must = [
        "Audit logs must capture login attempts and be sent to a central SIEM.",
        "System events shall be logged locally and stored for 3 years.",
        "Privileged access activities must be recorded in the security audit database.",
        "All application errors must be logged with timestamp and user ID details."
    ]
    l_conflict = [
        "SIEM log forwarding is prohibited due to privacy guidelines.",
        "Local log retention is prohibited; all logs must be deleted immediately after forwarding.",
        "Recording application user IDs in logs is prohibited under GDPR compliance.",
        "No audit trail logs shall be maintained for administrative activities."
    ]
    l_redundant = [
        "Successful and failed login events must be forwarded to the central SIEM.",
        "Audit logs must be preserved locally for a minimum period of 36 months.",
        "Admins are required to log all elevated commands in the security ledger.",
        "Error logs must document the exact time and operator ID for every exception."
    ]
    
    # Topic: mobile
    m_must = [
        "Personal mobile devices must run MDM agents before accessing corporate networks.",
        "Mobile phones must be locked with a 6-digit PIN and biometrics.",
        "Company data must be encrypted on all hand-held tablet devices."
    ]
    m_conflict = [
        "Employees are prohibited from installing MDM software on personal devices.",
        "Biometric device locks are prohibited on handheld hardware.",
        "Handheld tablet devices are exempt from encryption checks."
    ]
    
    # Topic: physical
    ph_must = [
        "Visitors must wear security badges visible at all times in the facility.",
        "Server room doors must remain physically locked and monitored by CCTV.",
        "All users must physical as per company standards.",
        "All users required physical as per company standards."
    ]
    ph_conflict = [
        "Security badges are not required for visitors accompanied by staff.",
        "Server room entryways shall remain unlocked during standard working hours.",
        "Physical is prohibited for all users."
    ]
    ph_redundant = [
        "All users recommended physical as per company standards.",
        "All users shall physical as per company standards.",
        "All users should physical as per company standards."
    ]
    
    # Topic: patch
    patch_must = [
        "All users must patch as per company standards.",
        "All users required patch as per company standards."
    ]
    patch_conflict = [
        "Patch is prohibited for all users."
    ]
    patch_redundant = [
        "All users recommended patch as per company standards.",
        "All users shall patch as per company standards.",
        "All users should patch as per company standards."
    ]
    
    # Topic: provisioning
    prov_must = [
        "All users must provisioning as per company standards.",
        "All users required provisioning as per company standards."
    ]
    prov_conflict = [
        "Provisioning is prohibited for all users."
    ]
    prov_redundant = [
        "All users should provisioning as per company standards.",
        "All users shall provisioning as per company standards."
    ]
    
    # Topic: vendor
    v_must = [
        "Third-party vendors must sign non-disclosure agreements before receiving access.",
        "Vendor security postures must be audited annually by the risk team.",
        "All users must vendor as per company standards.",
        "All users required vendor as per company standards."
    ]
    v_conflict = [
        "Vendors are exempt from signing non-disclosure agreements for testing environments.",
        "Compliance reviews for third-party vendors are not required.",
        "Vendor is prohibited for all users."
    ]
    v_redundant = [
        "All users should vendor as per company standards.",
        "All users recommended vendor as per company standards.",
        "All users shall vendor as per company standards."
    ]
    
    # Topic: asset
    asset_must = [
        "All users must asset as per company standards.",
        "All users required asset as per company standards."
    ]
    asset_conflict = [
        "Asset is prohibited for all users."
    ]
    asset_redundant = [
        "All users should asset as per company standards.",
        "All users recommended asset as per company standards."
    ]
    
    # Topic: cloud
    cloud_must = [
        "All users must cloud as per company standards.",
        "All users required cloud as per company standards."
    ]
    cloud_conflict = [
        "Cloud is prohibited for all users."
    ]
    cloud_redundant = [
        "All users should cloud as per company standards.",
        "All users recommended cloud as per company standards.",
        "All users shall cloud as per company standards."
    ]
    
    # Topic: access
    access_must = [
        "All users must access as per company standards.",
        "All users required access as per company standards."
    ]
    access_conflict = [
        "Access is prohibited for all users."
    ]
    access_redundant = [
        "All users recommended access as per company standards.",
        "All users should access as per company standards.",
        "All users shall access as per company standards."
    ]
    
    # Topic: privacy
    priv_must = [
        "All users must privacy as per company standards.",
        "All users required privacy as per company standards."
    ]
    priv_conflict = [
        "Privacy is prohibited for all users."
    ]
    priv_redundant = [
        "All users should privacy as per company standards.",
        "All users recommended privacy as per company standards."
    ]
    
    # Topic: monitoring
    mon_must = [
        "All users must monitoring as per company standards.",
        "All users required monitoring as per company standards."
    ]
    mon_conflict = [
        "Monitoring is prohibited for all users."
    ]
    mon_redundant = [
        "All users shall monitoring as per company standards.",
        "All users should monitoring as per company standards."
    ]

    # Topic: data retention
    d_must = [
        "Customer transaction records must be retained for exactly 7 years.",
        "General communication backups shall be deleted after 180 days.",
        "All users must data retention as per company standards.",
        "All users required data retention as per company standards."
    ]
    d_conflict = [
        "Transaction records must be destroyed immediately after audit validation.",
        "All backup logs must be preserved indefinitely without deletion.",
        "Data Retention is prohibited for all users."
    ]
    d_redundant = [
        "All users recommended data retention as per company standards.",
        "All users should data retention as per company standards.",
        "All users shall data retention as per company standards."
    ]
    
    # Combine list for pairing helper
    topics_list = [
        ("password", p_must, p_conflict, p_redundant),
        ("logging", l_must, l_conflict, l_redundant),
        ("mobile", m_must, m_conflict, []),
        ("physical", ph_must, ph_conflict, ph_redundant),
        ("patch", patch_must, patch_conflict, patch_redundant),
        ("provisioning", prov_must, prov_conflict, prov_redundant),
        ("vendor", v_must, v_conflict, v_redundant),
        ("asset", asset_must, asset_conflict, asset_redundant),
        ("cloud", cloud_must, cloud_conflict, cloud_redundant),
        ("access", access_must, access_conflict, access_redundant),
        ("privacy", priv_must, priv_conflict, priv_redundant),
        ("monitoring", mon_must, mon_conflict, mon_redundant),
        ("data retention", d_must, d_conflict, d_redundant)
    ]
    
    pairs = []
    labels = []
    
    # Loop topics and build pairs
    for topic, must_list, conflict_list, redundant_list in topics_list:
        # 1. Build CONFLICT pairs (Must vs Conflict)
        for m in must_list:
            for c in conflict_list:
                pairs.append((m, c))
                labels.append("CONFLICT")
                
        # 2. Build REDUNDANT pairs (Must vs Redundant)
        if redundant_list:
            for i, m in enumerate(must_list):
                if i < len(redundant_list):
                    pairs.append((m, redundant_list[i]))
                    labels.append("REDUNDANT")
                    
        # 3. Build COMPLEMENTARY pairs (Must vs Must)
        for i in range(len(must_list)):
            for j in range(i + 1, len(must_list)):
                pairs.append((must_list[i], must_list[j]))
                labels.append("COMPLEMENTARY")

    # Boost REDUNDANT samples
    redundant_samples = [
        ("MFA is required for all administrative access.", "Multi-factor authentication must be enabled for admin accounts."),
        ("Backups must be encrypted using AES-256.", "It is mandatory to encrypt backup volumes with the AES-256 algorithm."),
        ("Passwords must be at least 12 characters in length.", "A minimum complexity of 12 characters is required for credentials."),
        ("Logs must be retained for 3 years.", "We require retention of log files for a period of 36 months."),
        ("All external endpoints must be scanned weekly.", "Weekly vulnerability scans are mandatory for all public interfaces."),
        ("Mobile devices must run MDM agents.", "Mobile device management enrollment is required for employee phones."),
        ("NDA agreements must be signed by all contractors.", "Every contractor is required to sign a non-disclosure agreement."),
        ("Deployments require peer reviews.", "No code changes shall be pushed to production without a pull request review."),
    ]
    for m, r in redundant_samples:
        for _ in range(7):
            pairs.append((m, r))
            labels.append("REDUNDANT")

    # Boost COMPLEMENTARY samples
    complementary_samples = [
        ("Passwords must be changed every 90 days.", "Passwords must be at least 12 characters long."),
        ("Audit logs must capture user IDs.", "Audit logs must be encrypted in transit."),
        ("Servers must be physically locked.", "CCTV cameras must monitor server room entryways."),
        ("MDM agents must be installed on cellphones.", "Corporate email access requires biometric device locking."),
        ("Vendors must undergo annual security review.", "Vendor NDAs must be signed before access."),
        ("Financial records must be stored for 7 years.", "Transaction logs must be backed up daily."),
    ]
    for c1, c2 in complementary_samples:
        for _ in range(7):
            pairs.append((c1, c2))
            labels.append("COMPLEMENTARY")

    # 4. Build UNRELATED pairs (cross-topic mixes)
    all_sentences = p_must + l_must + m_must + ph_must + v_must + d_must
    random.seed(42)
    for _ in range(150): # target balanced number
        sa = random.choice(all_sentences)
        sb = random.choice(all_sentences)
        # Verify different topics
        def get_topic(s):
            for t in ["password", "log", "mobile", "badge", "vendor", "retain"]:
                if t in s.lower(): return t
            return "general"
        if get_topic(sa) != get_topic(sb):
            pairs.append((sa, sb))
            labels.append("UNRELATED")
            
    print(f"Generated {len(pairs)} augmented training pairs from synthetic generation.")
    return pairs, labels

def load_data():
    data_dir = "sample_data"
    obs_file = os.path.join(data_dir, "obligation_extracts_labels.json")
    findings_file = os.path.join(data_dir, "findings_labels.json")
    
    with open(obs_file, "r") as f:
        all_obs = json.load(f)
    with open(findings_file, "r") as f:
        all_findings = json.load(f)
        
    pairs = []
    labels = []
    
    # Parse ground truth labels from dataset
    def get_label(p_a, p_b, topic):
        for f in all_findings:
            f_pa = f.get("policy_a", "")
            f_pb = f.get("policy_b", "")
            if (f_pa == p_a and f_pb == p_b) or (f_pa == p_b and f_pb == p_a):
                desc = f.get("description", "").lower()
                ftype = f.get("finding_type", "UNRELATED")
                if topic in desc or topic.replace(" ", "_") in desc or any(t in desc for t in topic.split()):
                    if ftype == "CONFLICT":
                        return "CONFLICT"
                    elif ftype == "REDUNDANCY":
                        return "REDUNDANT"
                    elif ftype == "COMPLEMENTARY":
                        return "COMPLEMENTARY"
        return "UNRELATED"

    # Build pairs from real dataset
    unrelated_count = 0
    for i in range(len(all_obs)):
        for j in range(i + 1, len(all_obs)):
            ob_a = all_obs[i]
            ob_b = all_obs[j]
            if ob_a["policy_file"] == ob_b["policy_file"]:
                continue
            topic_a = ob_a["topic"].replace("_", " ").lower()
            topic_b = ob_b["topic"].replace("_", " ").lower()
            
            if topic_a == topic_b:
                label = get_label(ob_a["policy_file"], ob_b["policy_file"], topic_a)
                if label == "UNRELATED":
                    unrelated_count += 1
                    if unrelated_count > 100: # Downsample unrelated to balance classes
                        continue
                pairs.append((ob_a["obligation_text"], ob_b["obligation_text"]))
                labels.append(label)
                
    # Combine real data with augmented synthetic data
    aug_pairs, aug_labels = generate_augmented_dataset()
    pairs.extend(aug_pairs)
    labels.extend(aug_labels)
    
    print(f"Total training dataset: {len(pairs)} instances.")
    print("Label distribution:", {lbl: labels.count(lbl) for lbl in set(labels)})
    return pairs, labels

# Generate embeddings locally
def get_embeddings(texts):
    from app.embedding.generator import EmbeddingService
    print(f"Vectorizing {len(texts)} texts using backend embedding service...")
    return np.array(EmbeddingService.get_embeddings(texts))

def train():
    pairs, labels = load_data()
    if not pairs:
        print("Error: No training pairs generated.")
        return
        
    texts_a = [p[0] for p in pairs]
    texts_b = [p[1] for p in pairs]
    
    # Run vectorizer (finishes in milliseconds)
    embs_a = get_embeddings(texts_a)
    embs_b = get_embeddings(texts_b)
    
    # Feature extraction
    features_list = []
    import re
    topics_vocab = ["physical", "patch", "retention", "provisioning", "third-party", "hr", "mobile", "api", "monitoring", "password", "logging", "vendor", "endpoint", "change", "encryption", "backup"]
    negations = ["not", "prohibit", "forbidden", "shall not", "must not", "never", "prohibited", "cannot"]

    for idx, (emb_a, emb_b) in enumerate(zip(embs_a, embs_b)):
        text_a = texts_a[idx]
        text_b = texts_b[idx]
        
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
        
        feat = np.hstack(([sim], abs_diff, prod, [overlap, neg_mismatch, topic_match]))
        features_list.append(feat)
        
    X = np.array(features_list)
    y = np.array(labels)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Training features shape: {X_train.shape}, Test features shape: {X_test.shape}")
    
    # Train Multi-Class Logistic Regression Model with balanced class weights
    clf = LogisticRegression(max_iter=1000, solver='lbfgs', class_weight='balanced')
    clf.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Training complete. Validation Accuracy: {acc * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the trained model
    os.makedirs("backend/app/conflict_engine", exist_ok=True)
    model_path = "backend/app/conflict_engine/conflict_classifier.joblib"
    joblib.dump(clf, model_path)
    print(f"Saved trained classifier weights to {model_path}")
    
    # Save few-shot prompt mappings
    few_shots = []
    for cls in ["CONFLICT", "REDUNDANT", "COMPLEMENTARY", "UNRELATED"]:
        indices = [i for i, lbl in enumerate(labels) if lbl == cls]
        for idx in indices[:2]:
            few_shots.append({
                "obligation_a": pairs[idx][0],
                "obligation_b": pairs[idx][1],
                "label": cls
            })
            
    few_shot_path = "backend/app/conflict_engine/few_shots.json"
    with open(few_shot_path, "w") as f:
        json.dump(few_shots, f, indent=2)
    print(f"Saved LLM few-shot alignment manifest to {few_shot_path}")

if __name__ == "__main__":
    train()
