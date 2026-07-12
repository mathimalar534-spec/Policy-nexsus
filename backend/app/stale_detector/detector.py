import logging
import re
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.config.config import settings
from app.models.models import Policy, PolicyVersion, Finding
from app.repositories.repositories import FindingRepository

logger = logging.getLogger(__name__)

class StaleDetector:
    @classmethod
    def check_policy_age(cls, db: Session, policy: Policy) -> bool:
        """
        Check if policy review date exceeds threshold. If so, create finding.
        """
        if not policy.last_reviewed_at:
            # Assume stale if no review date
            is_stale = True
            reviewed_str = "never reviewed"
        else:
            days_since_review = (date.today() - policy.last_reviewed_at).days
            is_stale = days_since_review > settings.STALE_POLICY_THRESHOLD_DAYS
            reviewed_str = f"last reviewed on {policy.last_reviewed_at}"

        if is_stale:
            # Check if STALE_POLICY finding already exists for this policy
            existing = db.query(Finding).filter(
                Finding.policy_id == policy.id,
                Finding.finding_subtype == "STALE_POLICY"
            ).first()
            
            if not existing:
                FindingRepository.create(db, {
                    "finding_type": "STALE",
                    "finding_subtype": "STALE_POLICY",
                    "severity": "MEDIUM",
                    "confidence": 1.0,
                    "policy_id": policy.id,
                    "description": f"Policy '{policy.title}' has exceeded its review threshold.",
                    "explanation": f"Policy was {reviewed_str}. The review threshold is {settings.STALE_POLICY_THRESHOLD_DAYS} days.",
                    "recommendation": "Perform a governance review, update the policy content, and refresh the review date."
                })
                return True
        return False

    @classmethod
    def check_stale_references(cls, db: Session, policy: Policy) -> int:
        """
        Scan policy text for deprecated technologies and create findings.
        """
        # Get latest version text content
        latest_version = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id
        ).order_by(PolicyVersion.version_number.desc()).first()
        
        if not latest_version:
            logger.warning(f"No text content found for policy {policy.id} to perform reference scan.")
            return 0

        text = latest_version.text_content
        findings_created = 0

        for tech in settings.DEPRECATED_TECHNOLOGIES:
            # Use word boundaries to search, case-insensitive
            # e.g., \bSHA1\b or \bTLS 1\.0\b
            escaped_tech = re.escape(tech)
            # Support dash/space variation (e.g. SHA-1 vs SHA1)
            pattern = rf"\b{escaped_tech}\b"
            if re.search(pattern, text, re.IGNORECASE):
                # Check if this stale reference finding already exists
                existing = db.query(Finding).filter(
                    Finding.policy_id == policy.id,
                    Finding.finding_subtype == "STALE_REFERENCE",
                    Finding.explanation.like(f"%{tech}%")
                ).first()
                
                if not existing:
                    FindingRepository.create(db, {
                        "finding_type": "STALE",
                        "finding_subtype": "STALE_REFERENCE",
                        "severity": "LOW",
                        "confidence": 0.95,
                        "policy_id": policy.id,
                        "description": f"Deprecated reference to '{tech}' found in policy '{policy.title}'.",
                        "explanation": f"The document references '{tech}', which is deprecated or insecure.",
                        "recommendation": f"Update the policy to replace '{tech}' with a modern security standard."
                    })
                    findings_created += 1
                    
        return findings_created

    @classmethod
    def scan_policy(cls, db: Session, policy_id: int) -> Dict[str, Any]:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            return {"stale_policy": False, "stale_references": 0}

        stale_policy = cls.check_policy_age(db, policy)
        stale_refs = cls.check_stale_references(db, policy)
        
        return {
            "stale_policy": stale_policy,
            "stale_references": stale_refs
        }

    @classmethod
    def scan_all_policies(cls, db: Session) -> Dict[str, int]:
        policies = db.query(Policy).all()
        total_stale_policies = 0
        total_stale_references = 0
        
        for p in policies:
            res = cls.scan_policy(db, p.id)
            if res["stale_policy"]:
                total_stale_policies += 1
            total_stale_references += res["stale_references"]
            
        return {
            "stale_policies_flagged": total_stale_policies,
            "stale_references_flagged": total_stale_references
        }
