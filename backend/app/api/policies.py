import os
import hashlib
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config.config import settings
from app.models.models import User, Policy, UploadHistory
from app.repositories.repositories import PolicyRepository, UploadHistoryRepository
from app.middleware.auth import RoleChecker, get_current_user
from app.policy_parser.parser import PolicyParser
from app.llm.llm_client import LLMClient
from app.repositories.repositories import ObligationRepository
from app.utils.async_runner import trigger_background_job
from app.services.tasks import detect_conflicts_task

router = APIRouter(prefix="/policies", tags=["Policies"])

# RBAC dependencies
require_auditor = RoleChecker(["Admin", "Auditor"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_policies(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    upload_ids = []
    
    for file in files:
        filename = file.filename
        file_ext = os.path.splitext(filename)[1].lower().strip('.')
        
        if file_ext not in ["pdf", "docx", "txt", "md", "markdown"]:
            UploadHistoryRepository.create(db, filename, "Error", f"Unsupported file extension: {file_ext}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension for file {filename}. Allowed: PDF, DOCX, TXT, MD"
            )
            
        try:
            # 1. Save file to disk
            file_name_saved = f"{hashlib.md5(filename.encode()).hexdigest()}_{filename}"
            save_path = os.path.join(settings.UPLOAD_DIR, file_name_saved)
            
            with open(save_path, "wb") as f:
                content = file.file.read()
                f.write(content)
                
            # Compute hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Check if policy with same hash already exists
            existing_policy = PolicyRepository.get_by_hash(db, file_hash)
            if existing_policy:
                UploadHistoryRepository.create(db, filename, "Success", f"Reused existing policy ID {existing_policy.id}")
                upload_ids.append(existing_policy.id)
                continue

            # 2. Extract and normalize text
            raw_text = PolicyParser.extract_text(save_path, file_ext)
            
            # 3. Create Policy
            policy_data = {
                "title": os.path.splitext(filename)[0].replace("_", " ").title(),
                "description": f"Uploaded policy file: {filename}",
                "file_path": save_path,
                "file_hash": file_hash,
                "file_type": file_ext,
                "status": "active",
                "owner_id": current_user.id
            }
            policy = PolicyRepository.create(db, policy_data)
            
            # Save Version 1.0
            PolicyRepository.add_version(db, policy.id, "v1.0", raw_text, current_user.id)
            
            # 4. Obligation Extraction
            # Extract obligations using LLM or fallback heuristics
            extracted_obligations = LLMClient.extract_obligations(raw_text)
            for entry in extracted_obligations:
                ObligationRepository.create(db, {
                    "policy_id": policy.id,
                    "text_content": entry.get("obligation_text", ""),
                    "subject": entry.get("subject", "Staff"),
                    "action": entry.get("action", "comply"),
                    "object": entry.get("object", "general"),
                    "topic": entry.get("topic", "general"),
                    "strength": entry.get("strength", "must"),
                    "scope": entry.get("scope", "all"),
                    "condition": entry.get("condition", "under all circumstances")
                })
                
            # Create standard policy metadata
            meta_dict = {
                "author": current_user.username,
                "department": "Uploaded",
                "version": "v1.0",
                "last_reviewed": datetime.utcnow().date().isoformat()
            }
            PolicyRepository.add_metadata(db, policy.id, meta_dict)
            
            # Log upload success
            UploadHistoryRepository.create(db, filename, "Success")
            upload_ids.append(policy.id)
            
            # 5. Trigger background celery job for vector indexing and conflict scans
            trigger_background_job(background_tasks, detect_conflicts_task, policy.id)
            
        except Exception as e:
            UploadHistoryRepository.create(db, filename, "Error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process file {filename}: {str(e)}"
            )
            
    return {"upload_history_ids": upload_ids, "status": "processing"}

@router.post("/compare")
def compare_two_policies(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """
    POST /policies/compare - Upload exactly two policies and find contradictions between them.
    Saves both policies and returns the side-by-side analysis findings.
    """
    policy_ids = []
    policy_records = []
    
    # Helper to process a single file upload
    def process_policy_file(file: UploadFile) -> Policy:
        filename = file.filename
        file_ext = os.path.splitext(filename)[1].lower().strip('.')
        if file_ext not in ["pdf", "docx", "txt", "md", "markdown"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file: {filename}. Allowed: PDF, DOCX, TXT, MD"
            )
        try:
            # Save file
            file_name_saved = f"compare_{hashlib.md5(filename.encode()).hexdigest()}_{filename}"
            save_path = os.path.join(settings.UPLOAD_DIR, file_name_saved)
            with open(save_path, "wb") as f:
                content = file.file.read()
                f.write(content)
            
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Check if exists
            existing = PolicyRepository.get_by_hash(db, file_hash)
            if existing:
                return existing

            # Extract
            raw_text = PolicyParser.extract_text(save_path, file_ext)
            
            policy = PolicyRepository.create(db, {
                "title": os.path.splitext(filename)[0].replace("_", " ").title(),
                "description": f"Uploaded comparison policy: {filename}",
                "file_path": save_path,
                "file_hash": file_hash,
                "file_type": file_ext,
                "status": "active",
                "owner_id": current_user.id
            })
            
            PolicyRepository.add_version(db, policy.id, "v1.0", raw_text, current_user.id)
            
            # Extract obligations
            extracted = LLMClient.extract_obligations(raw_text)
            for entry in extracted:
                ObligationRepository.create(db, {
                    "policy_id": policy.id,
                    "text_content": entry.get("obligation_text", ""),
                    "subject": entry.get("subject", "Staff"),
                    "action": entry.get("action", "comply"),
                    "object": entry.get("object", "general"),
                    "topic": entry.get("topic", "general"),
                    "strength": entry.get("strength", "must"),
                    "scope": entry.get("scope", "all"),
                    "condition": entry.get("condition", "under all circumstances")
                })
                
            # Add metadata
            meta_dict = {
                "author": current_user.username,
                "department": "Comparison",
                "version": "v1.0",
                "last_reviewed": datetime.utcnow().date().isoformat()
            }
            PolicyRepository.add_metadata(db, policy.id, meta_dict)
            return policy
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing file {filename}: {str(e)}"
            )

    # 1. Ingest both files
    policy_a = process_policy_file(file_a)
    policy_b = process_policy_file(file_b)
    
    # 2. Extract obligations
    obs_a = db.query(Obligation).filter(Obligation.policy_id == policy_a.id).all()
    obs_b = db.query(Obligation).filter(Obligation.policy_id == policy_b.id).all()
    
    # 3. Generate embeddings & register FAISS
    from app.embedding.generator import EmbeddingService
    from app.vectorstore.faiss_store import vector_store
    
    for o in obs_a + obs_b:
        if not o.embeddings:
            vec = EmbeddingService.get_embedding(o.text_content)
            ObligationRepository.save_embedding(db, o.id, vec)
            vector_store.add_vectors([o.id], [vec])
    vector_store.save()

    # 4. Compare all obligations A with B directly
    comparison_findings = []
    
    for o_a in obs_a:
        for o_b in obs_b:
            # Check if topics are related or overlap
            if o_a.topic == o_b.topic or o_a.topic in o_b.text_content.lower() or o_b.topic in o_a.text_content.lower():
                # Check existing
                existing_f = db.query(Finding).filter(
                    Finding.obligation_a_id == min(o_a.id, o_b.id),
                    Finding.obligation_b_id == max(o_a.id, o_b.id)
                ).first()
                
                if existing_f:
                    comparison_findings.append(existing_f)
                    continue
                    
                # Run LLM conflict classifier
                analysis = LLMClient.analyze_conflict(o_a.text_content, o_b.text_content, o_a.topic)
                ftype = analysis.get("finding_type", "UNRELATED")
                
                if ftype in ["CONFLICT", "REDUNDANCY", "COMPLEMENTARY", "FALSE_POSITIVE_PRONE"]:
                    f_data = {
                        "finding_type": ftype,
                        "finding_subtype": analysis.get("finding_subtype", ftype),
                        "severity": analysis.get("severity", "LOW"),
                        "confidence": float(analysis.get("confidence", 1.0)),
                        "policy_a_id": policy_a.id,
                        "policy_b_id": policy_b.id,
                        "obligation_a_id": o_a.id,
                        "obligation_b_id": o_b.id,
                        "description": analysis.get("description", ""),
                        "explanation": analysis.get("explanation", ""),
                        "recommendation": analysis.get("recommendation", "")
                    }
                    new_f = FindingRepository.create(db, f_data)
                    comparison_findings.append(new_f)

    # 5. Format output
    return {
        "policy_a": {
            "id": policy_a.id,
            "title": policy_a.title,
            "obligations": [{"id": o.id, "text": o.text_content} for o in obs_a]
        },
        "policy_b": {
            "id": policy_b.id,
            "title": policy_b.title,
            "obligations": [{"id": o.id, "text": o.text_content} for o in obs_b]
        },
        "findings": [
            {
                "id": f.id,
                "finding_type": f.finding_type,
                "finding_subtype": f.finding_subtype,
                "severity": f.severity,
                "confidence": f.confidence,
                "obligation_a_text": db.query(Obligation).filter(Obligation.id == f.obligation_a_id).first().text_content,
                "obligation_b_text": db.query(Obligation).filter(Obligation.id == f.obligation_b_id).first().text_content,
                "description": f.description,
                "explanation": f.explanation,
                "recommendation": f.recommendation
            }
            for f in comparison_findings
        ]
    }
