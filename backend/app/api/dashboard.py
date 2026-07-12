from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database.session import get_db
from app.models.models import Policy, Obligation, Finding, PolicyMetadata
from app.dashboard.risk_engine import RiskEngine
from app.schemas.schemas import DashboardSummary, DashboardConflicts, DashboardRedundancy, DashboardStale, GovernanceScoreResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, date

router = APIRouter(prefix="/dashboard", tags=["Dashboard Operations"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_policies = db.query(Policy).count()
    total_obligations = db.query(Obligation).count()
    total_findings = db.query(Finding).count()
    
    active_conflicts = db.query(Finding).filter(
        Finding.finding_type == "CONFLICT"
    ).count()
    
    redundancies = db.query(Finding).filter(
        Finding.finding_subtype == "REDUNDANCY"
    ).count()
    
    stale_policies = db.query(Finding).filter(
        Finding.finding_subtype == "STALE_POLICY"
    ).count()
    
    stale_references = db.query(Finding).filter(
        Finding.finding_subtype == "STALE_REFERENCE"
    ).count()
    
    risk_score_data = RiskEngine.calculate_governance_score(db)
    
    return DashboardSummary(
        total_policies=total_policies,
        total_obligations=total_obligations,
        total_findings=total_findings,
        active_conflicts=active_conflicts,
        redundancies=redundancies,
        stale_policies=stale_policies,
        stale_references=stale_references,
        governance_score=risk_score_data["governance_score"]
    )

@router.get("/conflicts", response_model=DashboardConflicts)
def get_dashboard_conflicts(db: Session = Depends(get_db)):
    findings = db.query(Finding).filter(Finding.finding_type == "CONFLICT").all()
    results = []
    for f in findings:
        pol_a = db.query(Policy).filter(Policy.id == f.policy_a_id).first()
        pol_b = db.query(Policy).filter(Policy.id == f.policy_b_id).first()
        results.append({
            "policy_a": pol_a.title if pol_a else "Unknown",
            "policy_b": pol_b.title if pol_b else "Unknown",
            "subtype": f.finding_subtype,
            "severity": f.severity,
            "description": f.description
        })
    return {"conflicts": results, "total": len(results)}

@router.get("/redundancy", response_model=DashboardRedundancy)
def get_dashboard_redundancy(db: Session = Depends(get_db)):
    findings = db.query(Finding).filter(Finding.finding_subtype == "REDUNDANCY").all()
    results = []
    for f in findings:
        pol_a = db.query(Policy).filter(Policy.id == f.policy_a_id).first()
        pol_b = db.query(Policy).filter(Policy.id == f.policy_b_id).first()
        results.append({
            "policy_a": pol_a.title if pol_a else "Unknown",
            "policy_b": pol_b.title if pol_b else "Unknown",
            "description": f.description,
            "explanation": f.explanation or ""
        })
    return {"redundancies": results, "total": len(results)}

@router.get("/stale", response_model=DashboardStale)
def get_dashboard_stale(db: Session = Depends(get_db)):
    findings = db.query(Finding).filter(Finding.finding_type == "STALE").all()
    results = []
    for f in findings:
        pol = db.query(Policy).filter(Policy.id == f.policy_id).first()
        results.append({
            "policy": pol.title if pol else "Unknown",
            "subtype": f.finding_subtype,
            "last_reviewed": str(pol.last_reviewed_at) if pol and pol.last_reviewed_at else "Never",
            "description": f.description,
            "explanation": f.explanation or ""
        })
    return {"stale_items": results, "total": len(results)}

@router.get("/policies")
def get_dashboard_policies(db: Session = Depends(get_db)):
    policies = db.query(Policy).all()
    results = []
    for p in policies:
        # Get metadata
        meta = db.query(PolicyMetadata).filter(PolicyMetadata.policy_id == p.id).all()
        meta_dict = {m.key: m.value for m in meta}
        
        # Count findings for this policy
        findings_count = db.query(Finding).filter(
            or_(
                Finding.policy_id == p.id,
                Finding.policy_a_id == p.id,
                Finding.policy_b_id == p.id
            )
        ).count()
        
        results.append({
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "author": meta_dict.get("author", "Unknown"),
            "department": meta_dict.get("department", "General"),
            "version": meta_dict.get("version", "1.0"),
            "last_reviewed": meta_dict.get("last_reviewed", "Never"),
            "findings_count": findings_count
        })
    return results

@router.get("/search")
def search_dashboard(
    db: Session = Depends(get_db),
    policy: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_str: Optional[str] = Query(None, alias="date")
):
    """
    Search and filter findings based on policy metadata, severity, status, topic, author.
    """
    query = db.query(Finding)
    
    # 1. Join policies to check for matches
    if policy or department or author or status or date_str:
        # Check either policy_id, policy_a_id or policy_b_id
        # We fetch filtered policy IDs first
        p_query = db.query(Policy.id)
        
        if policy:
            p_query = p_query.filter(Policy.title.ilike(f"%{policy}%"))
        if status:
            p_query = p_query.filter(Policy.status == status)
        if date_str:
            try:
                p_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                p_query = p_query.filter(Policy.last_reviewed_at == p_date)
            except ValueError:
                pass
                
        # Join metadata for department and author
        if department:
            p_query = p_query.join(PolicyMetadata).filter(
                and_(PolicyMetadata.key == "department", PolicyMetadata.value.ilike(f"%{department}%"))
            )
        if author:
            p_query = p_query.join(PolicyMetadata).filter(
                and_(PolicyMetadata.key == "author", PolicyMetadata.value.ilike(f"%{author}%"))
            )
            
        policy_ids = [r[0] for r in p_query.all()]
        
        # Filter findings that involve these policies
        query = query.filter(
            or_(
                Finding.policy_id.in_(policy_ids),
                Finding.policy_a_id.in_(policy_ids),
                Finding.policy_b_id.in_(policy_ids)
            )
        )

    # 2. Filter findings severity
    if severity:
        query = query.filter(Finding.severity == severity.upper())
        
    # 3. Filter findings by topic (checks matching obligations)
    if topic:
        ob_query = db.query(Obligation.id).filter(Obligation.topic.ilike(f"%{topic}%"))
        ob_ids = [r[0] for r in ob_query.all()]
        query = query.filter(
            or_(
                Finding.obligation_a_id.in_(ob_ids),
                Finding.obligation_b_id.in_(ob_ids)
            )
        )

    findings = query.all()
    results = []
    
    for f in findings:
        pol_a = db.query(Policy).filter(Policy.id == f.policy_a_id).first() if f.policy_a_id else None
        pol_b = db.query(Policy).filter(Policy.id == f.policy_b_id).first() if f.policy_b_id else None
        pol = db.query(Policy).filter(Policy.id == f.policy_id).first() if f.policy_id else None
        
        results.append({
            "id": f.id,
            "finding_type": f.finding_type,
            "finding_subtype": f.finding_subtype,
            "severity": f.severity,
            "confidence": f.confidence,
            "policy_a": pol_a.title if pol_a else None,
            "policy_b": pol_b.title if pol_b else None,
            "policy": pol.title if pol else None,
            "description": f.description,
            "explanation": f.explanation,
            "recommendation": f.recommendation,
            "created_at": f.created_at
        })
        
    return results

@router.get("/filter")
def filter_dashboard(db: Session = Depends(get_db), **kwargs):
    # Map to search logic directly
    return search_dashboard(db, **kwargs)

@router.get("/analytics")
def get_dashboard_analytics(db: Session = Depends(get_db)):
    """
    Returns analytics aggregates of severity, subtype distribution, and department counts.
    """
    findings = db.query(Finding).all()
    
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    subtype_counts = {}
    dept_counts = {}
    
    for f in findings:
        # Severity
        sev = f.severity.upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Subtype
        sub = f.finding_subtype
        subtype_counts[sub] = subtype_counts.get(sub, 0) + 1
        
        # Resolve department for the involved policy
        p_id = f.policy_id or f.policy_a_id
        if p_id:
            dept_meta = db.query(PolicyMetadata).filter(
                PolicyMetadata.policy_id == p_id,
                PolicyMetadata.key == "department"
            ).first()
            dept = dept_meta.value if dept_meta else "General"
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

    return {
        "severity_distribution": severity_counts,
        "subtype_distribution": subtype_counts,
        "department_distribution": dept_counts
    }

@router.get("/risk-score", response_model=GovernanceScoreResponse)
def get_dashboard_risk_score(db: Session = Depends(get_db)):
    metrics = RiskEngine.calculate_governance_score(db)
    return GovernanceScoreResponse(
        governance_score=metrics["governance_score"],
        grade=metrics["grade"],
        deductions=metrics["deductions"]
    )
