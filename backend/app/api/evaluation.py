import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config.config import settings
from app.models.models import Finding, Policy
from app.schemas.schemas import EvaluationResponse, ConfusionMatrixSchema

router = APIRouter(prefix="/evaluation", tags=["Evaluation Operations"])
logger = logging.getLogger(__name__)

@router.get("", response_model=EvaluationResponse)
def get_evaluation_metrics(db: Session = Depends(get_db)):
    """
    GET /evaluation - Compares dynamically detected findings against findings_labels.json ground truth.
    Calculates Precision, Recall, Accuracy, F1 Score, and Confusion Matrix.
    """
    findings_path = os.path.join(settings.SAMPLE_DATA_DIR, "findings_labels.json")
    if not os.path.exists(findings_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ground truth findings_labels.json not found at {findings_path}"
        )
        
    with open(findings_path, "r", encoding="utf-8") as f:
        gt_findings = json.load(f)
        
    # Get all active policies from DB for mapping names to IDs
    policies = db.query(Policy).all()
    policy_id_map = {p.id: os.path.basename(p.file_path) for p in policies}
    policy_name_map = {os.path.basename(p.file_path): p.id for p in policies}

    # Fetch all dynamically detected findings in PostgreSQL
    detected_findings = db.query(Finding).all()
    
    # Separate GT into positive examples (actual conflicts, redundancies, stale items)
    # and negative validation examples (FALSE_POSITIVE_PRONE)
    gt_positives = []
    gt_negatives = []  # FALSE_POSITIVE_PRONE pairs
    
    for gt in gt_findings:
        subtype = gt.get("finding_subtype", "")
        if subtype == "FALSE_POSITIVE_PRONE":
            gt_negatives.append(gt)
        else:
            gt_positives.append(gt)
            
    # Track which detected findings matched to positive ground truths
    matched_detected_ids = set()
    
    # Calculate True Positives (TP) and False Negatives (FN)
    tp = 0
    fn = 0
    
    for gt in gt_positives:
        gt_type = gt["finding_type"]
        gt_subtype = gt["finding_subtype"]
        
        # Check if matched in detected
        found_match = False
        for df in detected_findings:
            if df.id in matched_detected_ids:
                continue
                
            # Check type alignment
            type_align = (df.finding_type == gt_type) or (df.finding_subtype == gt_subtype)
            if not type_align:
                continue
                
            # Check policy links
            if "policy_a" in gt and "policy_b" in gt:
                # Cross-policy check
                df_a_file = policy_id_map.get(df.policy_a_id)
                df_b_file = policy_id_map.get(df.policy_b_id)
                
                # Check both orders A-B and B-A
                if (df_a_file == gt["policy_a"] and df_b_file == gt["policy_b"]) or \
                   (df_a_file == gt["policy_b"] and df_b_file == gt["policy_a"]):
                    found_match = True
                    matched_detected_ids.add(df.id)
                    break
            elif "policy" in gt:
                # Single policy check
                df_file = policy_id_map.get(df.policy_id)
                if df_file == gt["policy"]:
                    found_match = True
                    matched_detected_ids.add(df.id)
                    break
                    
        if found_match:
            tp += 1
        else:
            fn += 1
            
    # Calculate False Positives (FP)
    # FPs are detected findings that do NOT match any positive ground truth.
    # Note that detecting a conflict on a FALSE_POSITIVE_PRONE pair is also an FP.
    fp = len(detected_findings) - tp
    
    # Calculate True Negatives (TN)
    # Using the standard evaluation space:
    # 30 policies. Total policy pairs = 30 * 29 / 2 = 435.
    # 30 single-policy checkers.
    # Total classification tasks = 435 + 30 = 465.
    total_slots = 465
    tn = total_slots - (tp + fp + fn)
    # Ensure TN doesn't go below 0 due to custom datasets
    tn = max(0, tn)
    
    # Compute Metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return EvaluationResponse(
        precision=round(precision, 4),
        recall=round(recall, 4),
        accuracy=round(accuracy, 4),
        f1_score=round(f1_score, 4),
        confusion_matrix=ConfusionMatrixSchema(tp=tp, fp=fp, fn=fn, tn=tn),
        total_ground_truth=len(gt_positives),
        total_detected=len(detected_findings)
    )
