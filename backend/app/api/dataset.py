from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Policy, Obligation, Finding, Embedding
from app.repositories.repositories import FindingRepository
from app.database.seeder import seed_database
from app.vectorstore.faiss_store import vector_store
from app.utils.async_runner import trigger_background_job
from app.services.tasks import reload_dataset_task
from typing import List, Dict, Any

router = APIRouter(prefix="/dataset", tags=["Dataset Operations"])

@router.get("/statistics")
def get_dataset_statistics(db: Session = Depends(get_db)):
    """
    GET /dataset/statistics - Returns statistical counts of policies, obligations, and findings.
    """
    total_policies = db.query(Policy).count()
    total_obligations = db.query(Obligation).count()
    total_findings = db.query(Finding).count()
    
    # Subtype distribution
    findings = db.query(Finding.finding_subtype).all()
    subtypes = {}
    for f in findings:
        subtypes[f[0]] = subtypes.get(f[0], 0) + 1
        
    return {
        "policies_count": total_policies,
        "obligations_count": total_obligations,
        "findings_count": total_findings,
        "findings_subtype_distribution": subtypes
    }

@router.get("/policies")
def get_dataset_policies(db: Session = Depends(get_db)):
    """
    GET /dataset/policies - List all policies loaded from the dataset.
    """
    policies = db.query(Policy).all()
    return [{
        "id": p.id,
        "title": p.title,
        "file_path": p.file_path,
        "status": p.status,
        "last_reviewed_at": p.last_reviewed_at,
        "created_at": p.created_at
    } for p in policies]

@router.get("/obligations")
def get_dataset_obligations(db: Session = Depends(get_db)):
    """
    GET /dataset/obligations - List all obligations loaded from the dataset.
    """
    obligations = db.query(Obligation).all()
    return [{
        "id": o.id,
        "policy_id": o.policy_id,
        "text_content": o.text_content,
        "topic": o.topic,
        "strength": o.strength,
        "scope": o.scope
    } for o in obligations]

@router.get("/findings")
def get_dataset_findings(db: Session = Depends(get_db)):
    """
    GET /dataset/findings - List all findings loaded from the dataset.
    """
    findings = db.query(Finding).all()
    return [{
        "id": f.id,
        "type": f.finding_type,
        "subtype": f.finding_subtype,
        "severity": f.severity,
        "policy_a_id": f.policy_a_id,
        "policy_b_id": f.policy_b_id,
        "policy_id": f.policy_id,
        "description": f.description,
        "explanation": f.explanation
    } for f in findings]

@router.post("/reindex", status_code=status.HTTP_200_OK)
def trigger_reindex(db: Session = Depends(get_db)):
    """
    POST /dataset/reindex - Rebuilds the FAISS vector index from embeddings in the DB.
    """
    embeddings = db.query(Embedding).all()
    ob_ids = [e.obligation_id for e in embeddings]
    vectors = [e.vector for e in embeddings]
    
    vector_store.clear()
    if ob_ids:
        vector_store.add_vectors(ob_ids, vectors)
        vector_store.save()
        
    return {"status": "reindexed", "indexed_count": len(ob_ids)}

@router.post("/reload", status_code=status.HTTP_202_ACCEPTED)
def reload_dataset(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    POST /dataset/reload - Clears the database and triggers background data load from files.
    """
    trigger_background_job(background_tasks, reload_dataset_task)
    return {"status": "reload_triggered", "details": "Wiping database and reading metadata, obligations and findings in the background."}
