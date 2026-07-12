import logging
import os
from celery import shared_task
from app.services.celery_app import celery_app
from app.database.session import SessionLocal
from app.database.seeder import seed_database
from app.conflict_engine.detector import ConflictDetector
from app.stale_detector.detector import StaleDetector
from app.utils.report_generator import ReportGenerator
from app.models.models import Policy, Obligation, Report, Embedding
from app.repositories.repositories import ObligationRepository, ReportRepository
from app.embedding.generator import EmbeddingService
from app.vectorstore.faiss_store import vector_store

logger = logging.getLogger(__name__)

@celery_app.task(name="app.services.tasks.generate_embeddings_task")
def generate_embeddings_task(policy_id: int):
    """
    Background job to generate embeddings for all obligations of a policy and register them in FAISS.
    """
    logger.info(f"Starting embedding generation for policy {policy_id}")
    db = SessionLocal()
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            logger.error(f"Policy {policy_id} not found for embedding task")
            return
            
        obligations = db.query(Obligation).filter(Obligation.policy_id == policy_id).all()
        ob_ids = []
        vectors = []
        
        for ob in obligations:
            # Check if embedding already exists
            existing = db.query(Embedding).filter(Embedding.obligation_id == ob.id).first()
            if existing:
                continue
                
            vector = EmbeddingService.get_embedding(ob.text_content)
            ObligationRepository.save_embedding(db, ob.id, vector)
            ob_ids.append(ob.id)
            vectors.append(vector)
            
        if ob_ids:
            vector_store.load()
            vector_store.add_vectors(ob_ids, vectors)
            vector_store.save()
            logger.info(f"Generated and indexed {len(ob_ids)} embeddings for policy {policy_id}")
            
    except Exception as e:
        logger.exception(f"Error in embedding generation task for policy {policy_id}: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.services.tasks.detect_conflicts_task")
def detect_conflicts_task(policy_id: int):
    """
    Background job to run semantic conflict detection and stale reference checks for a policy.
    """
    logger.info(f"Starting conflict and staleness checks for policy {policy_id}")
    db = SessionLocal()
    try:
        # First ensure embeddings exist
        generate_embeddings_task.run(policy_id)
        
        # 1. Run stale checks
        StaleDetector.scan_policy(db, policy_id)
        
        # 2. Run conflict detection
        ConflictDetector.run_detection(db, policy_id)
        
        logger.info(f"Conflict check completed for policy {policy_id}")
    except Exception as e:
        logger.exception(f"Error in conflict checks task for policy {policy_id}: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.services.tasks.generate_pdf_report_task")
def generate_pdf_report_task(report_id: int):
    """
    Background job to build a ReportLab compliance audit PDF report.
    """
    logger.info(f"Starting report generation for report {report_id}")
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"Report {report_id} not found")
            return
            
        ReportRepository.update_status(db, report_id, "In Progress")
        
        # Define output path
        from app.config.config import settings
        file_name = f"compliance_report_{report_id}_{int(os.getpid())}.pdf"
        file_path = os.path.join(settings.UPLOAD_DIR, "reports", file_name)
        
        # Run report builder
        ReportGenerator.generate_pdf_report(db, file_path)
        
        # Calculate brief summary stats
        from app.models.models import Finding
        conflicts = db.query(Finding).filter(Finding.finding_type == "CONFLICT").count()
        stales = db.query(Finding).filter(Finding.finding_type == "STALE").count()
        redundant = db.query(Finding).filter(Finding.finding_type == "REDUNDANCY").count()
        summary_str = f"Audit complete. Findings: {conflicts} conflicts, {redundant} redundancies, {stales} stale items."
        
        # Update record
        ReportRepository.update_status(db, report_id, "Completed", file_path=file_path, summary=summary_str)
        logger.info(f"Report {report_id} successfully compiled at {file_path}")
        
    except Exception as e:
        logger.exception(f"Error generating report {report_id}: {str(e)}")
        ReportRepository.update_status(db, report_id, "Failed", summary=f"Compilation error: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.services.tasks.reload_dataset_task")
def reload_dataset_task():
    """
    Background job to wipe and reload database from JSON dataset files.
    """
    logger.info("Starting background dataset reload...")
    db = SessionLocal()
    try:
        seed_database(db, force=True)
        logger.info("Background dataset reload completed successfully.")
    except Exception as e:
        logger.exception(f"Error during background dataset reload: {str(e)}")
    finally:
        db.close()
