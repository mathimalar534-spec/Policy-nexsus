import os
import json
import hashlib
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.config.config import settings
from app.database.session import Base, engine
from app.models.models import Role, User, Policy, PolicyMetadata, PolicyVersion, Obligation, Finding, Embedding
from app.repositories.repositories import UserRepository, PolicyRepository, ObligationRepository, FindingRepository
from app.embedding.generator import EmbeddingService
from app.vectorstore.faiss_store import vector_store
from app.middleware.auth import get_password_hash

logger = logging.getLogger(__name__)

def compute_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def seed_database(db: Session, force: bool = False):
    """
    Seeds the database with roles, default users, policies, obligations, embeddings, and findings
    if it is empty or if force=True is passed.
    """
    # 1. Create tables if SQLite (migrations handle PostgreSQL in prod, but safe to create locally)
    if str(db.bind.url).startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    # Check if database is already seeded
    policy_count = db.query(Policy).count()
    if policy_count > 0 and not force:
        logger.info("Database already seeded. Skipping seeder.")
        # Make sure FAISS index is loaded
        vector_store.load()
        return False

    logger.info("Starting database seeding...")
    
    # Clear existing data if force reloading
    if force:
        db.query(Finding).delete()
        db.query(Embedding).delete()
        db.query(Obligation).delete()
        db.query(PolicyVersion).delete()
        db.query(PolicyMetadata).delete()
        db.query(Policy).delete()
        db.query(User).delete()
        db.query(Role).delete()
        db.commit()
        vector_store.clear()

    # 2. Seed Roles
    admin_role = UserRepository.create_role_if_not_exists(db, "Admin")
    auditor_role = UserRepository.create_role_if_not_exists(db, "Auditor")
    viewer_role = UserRepository.create_role_if_not_exists(db, "Viewer")

    # 3. Seed Default Users
    admin_user = UserRepository.get_by_username(db, "admin")
    if not admin_user:
        UserRepository.create(db, {
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("adminpassword"),
            "role_id": admin_role.id,
            "is_active": True
        })
        
    auditor_user = UserRepository.get_by_username(db, "auditor")
    if not auditor_user:
        auditor_user = UserRepository.create(db, {
            "username": "auditor",
            "email": "auditor@example.com",
            "hashed_password": get_password_hash("auditorpassword"),
            "role_id": auditor_role.id,
            "is_active": True
        })

    viewer_user = UserRepository.get_by_username(db, "viewer")
    if not viewer_user:
        UserRepository.create(db, {
            "username": "viewer",
            "email": "viewer@example.com",
            "hashed_password": get_password_hash("viewerpassword"),
            "role_id": viewer_role.id,
            "is_active": True
        })

    # Find a default creator
    creator = auditor_user or db.query(User).filter(User.username == "admin").first()
    creator_id = creator.id if creator else 1

    # 4. Load Policy Metadata & Files
    metadata_path = os.path.join(settings.SAMPLE_DATA_DIR, "policy_metadata.json")
    if not os.path.exists(metadata_path):
        logger.error(f"Sample data policy_metadata.json not found at {metadata_path}!")
        return False

    with open(metadata_path, "r", encoding="utf-8") as f:
        policies_meta = json.load(f)

    # Keep track of file -> database policy ID mapping
    policy_filename_map = {}

    for entry in policies_meta:
        filename = entry["file"]
        policy_file_path = os.path.join(settings.SAMPLE_DATA_DIR, "policies", filename)
        
        # Read content
        text_content = ""
        file_hash = ""
        if os.path.exists(policy_file_path):
            with open(policy_file_path, "r", encoding="utf-8") as pf:
                text_content = pf.read()
            file_hash = compute_file_hash(text_content)
        else:
            logger.warning(f"Policy file {filename} not found at {policy_file_path}. Creating blank version.")
            text_content = f"# {entry['title']}\n\nThis is a placeholder content for policy."
            file_hash = compute_file_hash(text_content)

        last_reviewed = None
        if entry["last_reviewed"]:
            try:
                last_reviewed = datetime.strptime(entry["last_reviewed"], "%Y-%m-%d").date()
            except ValueError:
                pass

        # Create policy
        policy = PolicyRepository.create(db, {
            "title": entry["title"],
            "description": f"Auditable compliance policy for {entry['department']} department.",
            "file_path": policy_file_path,
            "file_hash": file_hash,
            "file_type": "md",
            "status": entry["status"],
            "last_reviewed_at": last_reviewed,
            "owner_id": creator_id
        })

        policy_filename_map[filename] = policy.id

        # Add versions
        PolicyRepository.add_version(db, policy.id, entry["version"], text_content, creator_id)

        # Add Metadata
        meta_dict = {
            "author": entry["author"],
            "department": entry["department"],
            "version": entry["version"],
            "last_reviewed": entry["last_reviewed"]
        }
        PolicyRepository.add_metadata(db, policy.id, meta_dict)

    # 5. Load Obligations & Generate Embeddings
    obligations_path = os.path.join(settings.SAMPLE_DATA_DIR, "obligation_extracts_labels.json")
    if not os.path.exists(obligations_path):
        logger.error(f"Sample data obligation_extracts_labels.json not found at {obligations_path}!")
        return False

    with open(obligations_path, "r", encoding="utf-8") as f:
        obligations_meta = json.load(f)

    # Group all obligation texts to generate embeddings in batch (faster)
    texts_to_embed = [ob["obligation_text"] for ob in obligations_meta]
    logger.info(f"Generating embeddings for {len(texts_to_embed)} obligations in batch...")
    vectors = EmbeddingService.get_embeddings(texts_to_embed)

    vector_store.clear()
    ob_ids = []
    
    for idx, entry in enumerate(obligations_meta):
        policy_file = entry["policy_file"]
        policy_id = policy_filename_map.get(policy_file)
        
        if not policy_id:
            logger.warning(f"Could not map obligation to policy: {policy_file}. Skipping.")
            continue

        topic = entry.get("topic", "general")
        strength = entry.get("strength", "must")
        scope = entry.get("scope", "all")
        
        # Save obligation
        ob = ObligationRepository.create(db, {
            "policy_id": policy_id,
            "text_content": entry["obligation_text"],
            "subject": scope.capitalize() if scope != "all" else "Staff",
            "action": "comply",
            "object": topic,
            "topic": topic,
            "strength": strength,
            "scope": scope,
            "condition": "under all circumstances"
        })
        
        # Save embedding
        ObligationRepository.save_embedding(db, ob.id, vectors[idx])
        ob_ids.append(ob.id)

    # Add all vectors to FAISS and save index
    logger.info("Syncing vector store and writing FAISS index...")
    vector_store.add_vectors(ob_ids, vectors)
    vector_store.save()

    # 6. Load Labelled Findings
    findings_path = os.path.join(settings.SAMPLE_DATA_DIR, "findings_labels.json")
    if not os.path.exists(findings_path):
        logger.error(f"Sample data findings_labels.json not found at {findings_path}!")
        return False

    with open(findings_path, "r", encoding="utf-8") as f:
        findings_meta = json.load(f)

    for entry in findings_meta:
        finding_type = entry["finding_type"]
        subtype = entry["finding_subtype"]
        severity = entry.get("severity", "LOW")
        description = entry["description"]
        explanation = entry.get("explanation", "")
        
        finding_data = {
            "finding_type": finding_type,
            "finding_subtype": subtype,
            "severity": severity,
            "confidence": 1.0,
            "description": description,
            "explanation": explanation,
            "recommendation": "Perform policy alignments as detailed in description."
        }

        # Single policy finding
        if "policy" in entry:
            policy_id = policy_filename_map.get(entry["policy"])
            if policy_id:
                finding_data["policy_id"] = policy_id

        # Cross policy finding
        if "policy_a" in entry and "policy_b" in entry:
            policy_a_id = policy_filename_map.get(entry["policy_a"])
            policy_b_id = policy_filename_map.get(entry["policy_b"])
            if policy_a_id and policy_b_id:
                finding_data["policy_a_id"] = policy_a_id
                finding_data["policy_b_id"] = policy_b_id

        FindingRepository.create(db, finding_data)

    logger.info("Database seeding completed successfully.")
    return True
