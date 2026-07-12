import logging
from sqlalchemy.orm import Session
from app.models.models import Policy, Obligation, Finding
from app.repositories.repositories import FindingRepository, ObligationRepository
from app.vectorstore.faiss_store import vector_store
from app.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ConflictDetector:
    @classmethod
    def run_detection(cls, db: Session, policy_id: int, similarity_threshold: float = 0.5):
        """
        Runs conflict detection for a specific policy against all other policies
        using vector similarity search followed by LLM-based classification.
        """
        logger.info(f"Running conflict detection for policy ID {policy_id}...")
        
        # Get obligations of the policy
        obligations = db.query(Obligation).filter(Obligation.policy_id == policy_id).all()
        if not obligations:
            logger.info(f"No obligations found for policy ID {policy_id}. Skipping detection.")
            return

        findings_created = 0

        for ob in obligations:
            # Generate embedding vector for the obligation
            # Fetch from DB if already generated, otherwise generate
            emb_record = ob.embeddings
            if not emb_record:
                # Fallback generate dynamically
                from app.embedding.generator import EmbeddingService
                try:
                    vector = EmbeddingService.get_embedding(ob.text_content)
                    emb_record = ObligationRepository.save_embedding(db, ob.id, vector)
                    # Add to vector store
                    vector_store.add_vectors([ob.id], [vector])
                    vector_store.save()
                except Exception as e:
                    logger.error(f"Error generating embedding for obligation {ob.id}: {str(e)}")
                    continue
            else:
                vector = emb_record[0].vector

            # Search vector store for top K similar obligations
            # We fetch top 10 since some matches might belong to the same policy
            matches = vector_store.search(vector, k=10)
            
            for match_ob_id, sim in matches:
                if match_ob_id == ob.id:
                    continue  # Do not compare with self
                    
                if sim < similarity_threshold:
                    continue  # Ignore low-similarity matches
                    
                # Fetch matching obligation details
                match_ob = db.query(Obligation).filter(Obligation.id == match_ob_id).first()
                if not match_ob:
                    continue
                    
                # Ensure they belong to different policies
                if match_ob.policy_id == ob.policy_id:
                    continue
                    
                # Order consistently to prevent duplicate checks (ob_a always has lower policy ID)
                if ob.policy_id < match_ob.policy_id:
                    ob_a, ob_b = ob, match_ob
                else:
                    ob_a, ob_b = match_ob, ob
                    
                # Check if a finding already exists for this pair of obligations
                existing = db.query(Finding).filter(
                    Finding.obligation_a_id == ob_a.id,
                    Finding.obligation_b_id == ob_b.id
                ).first()
                if existing:
                    continue
                    
                # Analyze relationship via LLM client
                analysis = LLMClient.analyze_conflict(
                    ob_a.text_content, 
                    ob_b.text_content, 
                    topic=ob_a.topic or ob_b.topic or ""
                )
                
                finding_type = analysis.get("finding_type", "UNRELATED")
                
                # We only record if it's CONFLICT, REDUNDANCY, COMPLEMENTARY, or FALSE_POSITIVE_PRONE
                if finding_type in ["CONFLICT", "REDUNDANCY", "COMPLEMENTARY", "FALSE_POSITIVE_PRONE"]:
                    finding_data = {
                        "finding_type": finding_type,
                        "finding_subtype": analysis.get("finding_subtype", finding_type),
                        "severity": analysis.get("severity", "LOW"),
                        "confidence": float(analysis.get("confidence", 1.0)),
                        "policy_a_id": ob_a.policy_id,
                        "policy_b_id": ob_b.policy_id,
                        "obligation_a_id": ob_a.id,
                        "obligation_b_id": ob_b.id,
                        "description": analysis.get("description", "Potential relationship detected."),
                        "explanation": analysis.get("explanation", ""),
                        "recommendation": analysis.get("recommendation", "")
                    }
                    
                    FindingRepository.create(db, finding_data)
                    findings_created += 1

        logger.info(f"Conflict detection completed for policy ID {policy_id}. Created {findings_created} findings.")
        return findings_created

    @classmethod
    def run_all_detection(cls, db: Session, similarity_threshold: float = 0.5):
        """
        Runs conflict detection across all policies in the database.
        """
        policies = db.query(Policy).all()
        total_created = 0
        for p in policies:
            created = cls.run_detection(db, p.id, similarity_threshold)
            if created:
                total_created += created
        return total_created
