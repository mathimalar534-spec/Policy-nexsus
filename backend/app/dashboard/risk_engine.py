from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models.models import Finding, Policy

class RiskEngine:
    @classmethod
    def calculate_governance_score(cls, db: Session) -> Dict[str, Any]:
        """
        Calculates the overall Governance Score (0 to 100) based on detected findings.
        """
        findings = db.query(Finding).all()
        
        # Base score
        score = 100.0
        
        # Deduction weights
        weights = {
            "DIRECT_CONFLICT": 5.0,
            "PARTIAL_CONFLICT": 3.0,
            "REDUNDANCY": 1.5,
            "STALE_POLICY": 4.0,
            "STALE_REFERENCE": 2.0,
            "FALSE_POSITIVE_PRONE": 0.0  # False alarm prone has no governance deduction
        }
        
        deductions = {
            "DIRECT_CONFLICT": 0.0,
            "PARTIAL_CONFLICT": 0.0,
            "REDUNDANCY": 0.0,
            "STALE_POLICY": 0.0,
            "STALE_REFERENCE": 0.0
        }
        
        for f in findings:
            subtype = f.finding_subtype
            if subtype in weights:
                deduction_val = weights[subtype]
                score -= deduction_val
                if subtype in deductions:
                    deductions[subtype] += deduction_val
                    
        # Clamp score
        score = max(0.0, min(100.0, score))
        score = round(score, 2)
        
        # Determine Grade
        if score >= 90.0:
            grade = "A (Excellent Governance)"
        elif score >= 80.0:
            grade = "B (Good Governance)"
        elif score >= 70.0:
            grade = "C (Needs Attention)"
        elif score >= 60.0:
            grade = "D (High Risk)"
        else:
            grade = "F (Critical Audit Failure)"
            
        return {
            "governance_score": score,
            "grade": grade,
            "deductions": deductions
        }
