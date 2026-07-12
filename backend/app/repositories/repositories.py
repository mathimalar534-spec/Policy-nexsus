from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from app.models.models import User, Role, Policy, PolicyMetadata, PolicyVersion, Obligation, Embedding, Finding, Report, AuditLog, UploadHistory

class UserRepository:
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, user_data: Dict[str, Any]) -> User:
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_role_by_name(db: Session, role_name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name == role_name).first()

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
        return db.query(Role).filter(Role.id == role_id).first()

    @staticmethod
    def create_role_if_not_exists(db: Session, role_name: str) -> Role:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name)
            db.add(role)
            db.commit()
            db.refresh(role)
        return role

class PolicyRepository:
    @staticmethod
    def get_by_id(db: Session, policy_id: int) -> Optional[Policy]:
        return db.query(Policy).filter(Policy.id == policy_id).first()

    @staticmethod
    def get_by_filename(db: Session, filename: str) -> Optional[Policy]:
        # Filename can be mapped from metadata file key or file_path basename
        return db.query(Policy).filter(Policy.file_path.like(f"%{filename}")).first()

    @staticmethod
    def get_by_hash(db: Session, file_hash: str) -> Optional[Policy]:
        return db.query(Policy).filter(Policy.file_hash == file_hash).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100, **filters) -> List[Policy]:
        query = db.query(Policy)
        
        # Apply filters dynamically
        if "title" in filters and filters["title"]:
            query = query.filter(Policy.title.ilike(f"%{filters['title']}%"))
        if "status" in filters and filters["status"]:
            query = query.filter(Policy.status == filters["status"])
        if "author" in filters and filters["author"]:
            # Search author in metadata
            query = query.join(PolicyMetadata).filter(
                and_(PolicyMetadata.key == "author", PolicyMetadata.value.ilike(f"%{filters['author']}%"))
            )
        if "department" in filters and filters["department"]:
            # Search department in metadata
            query = query.join(PolicyMetadata).filter(
                and_(PolicyMetadata.key == "department", PolicyMetadata.value.ilike(f"%{filters['department']}%"))
            )
            
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, policy_data: Dict[str, Any]) -> Policy:
        policy = Policy(**policy_data)
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def add_metadata(db: Session, policy_id: int, metadata: Dict[str, str]):
        for k, v in metadata.items():
            meta = PolicyMetadata(policy_id=policy_id, key=k, value=str(v))
            db.add(meta)
        db.commit()

    @staticmethod
    def add_version(db: Session, policy_id: int, version_num: str, text: str, user_id: Optional[int] = None) -> PolicyVersion:
        version = PolicyVersion(
            policy_id=policy_id,
            version_number=version_num,
            text_content=text,
            created_by=user_id
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def update_status(db: Session, policy_id: int, status: str) -> Optional[Policy]:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if policy:
            policy.status = status
            db.commit()
            db.refresh(policy)
        return policy

    @staticmethod
    def delete(db: Session, policy_id: int) -> bool:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if policy:
            db.delete(policy)
            db.commit()
            return True
        return False

class ObligationRepository:
    @staticmethod
    def get_by_id(db: Session, obligation_id: int) -> Optional[Obligation]:
        return db.query(Obligation).filter(Obligation.id == obligation_id).first()

    @staticmethod
    def list(db: Session, policy_id: Optional[int] = None, skip: int = 0, limit: int = 100, topic: Optional[str] = None) -> List[Obligation]:
        query = db.query(Obligation)
        if policy_id is not None:
            query = query.filter(Obligation.policy_id == policy_id)
        if topic:
            query = query.filter(Obligation.topic.ilike(f"%{topic}%"))
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, ob_data: Dict[str, Any]) -> Obligation:
        ob = Obligation(**ob_data)
        db.add(ob)
        db.commit()
        db.refresh(ob)
        return ob

    @staticmethod
    def save_embedding(db: Session, obligation_id: int, vector: List[float]) -> Embedding:
        embedding = Embedding(obligation_id=obligation_id, vector=vector)
        db.add(embedding)
        db.commit()
        db.refresh(embedding)
        return embedding

    @staticmethod
    def get_embeddings_map(db: Session) -> List[Dict[str, Any]]:
        # Fetch obligations and their embeddings
        results = db.query(Obligation.id, Embedding.vector).join(Embedding).all()
        return [{"id": r[0], "vector": r[1]} for r in results]

class FindingRepository:
    @staticmethod
    def create(db: Session, finding_data: Dict[str, Any]) -> Finding:
        finding = Finding(**finding_data)
        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100, **filters) -> List[Finding]:
        query = db.query(Finding)
        if "finding_type" in filters and filters["finding_type"]:
            query = query.filter(Finding.finding_type == filters["finding_type"])
        if "finding_subtype" in filters and filters["finding_subtype"]:
            query = query.filter(Finding.finding_subtype == filters["finding_subtype"])
        if "severity" in filters and filters["severity"]:
            query = query.filter(Finding.severity == filters["severity"])
        if "policy_id" in filters and filters["policy_id"]:
            # Filters finding affecting a specific policy (either single-policy or A/B)
            p_id = filters["policy_id"]
            query = query.filter(
                or_(
                    Finding.policy_id == p_id,
                    Finding.policy_a_id == p_id,
                    Finding.policy_b_id == p_id
                )
            )
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def delete_all(db: Session):
        db.query(Finding).delete()
        db.commit()

class ReportRepository:
    @staticmethod
    def create(db: Session, report_data: Dict[str, Any]) -> Report:
        report = Report(**report_data)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_by_id(db: Session, report_id: int) -> Optional[Report]:
        return db.query(Report).filter(Report.id == report_id).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50) -> List[Report]:
        return db.query(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, report_id: int, status: str, file_path: Optional[str] = None, summary: Optional[str] = None) -> Optional[Report]:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = status
            if file_path:
                report.file_path = file_path
            if summary:
                report.summary = summary
            db.commit()
            db.refresh(report)
        return report

class AuditLogRepository:
    @staticmethod
    def create(db: Session, user_id: Optional[int], action: str, details: str, ip: Optional[str] = None) -> AuditLog:
        log = AuditLog(user_id=user_id, action=action, details=details, ip_address=ip)
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

class UploadHistoryRepository:
    @staticmethod
    def create(db: Session, filename: str, status: str, error_message: Optional[str] = None) -> UploadHistory:
        hist = UploadHistory(filename=filename, status=status, error_message=error_message)
        db.add(hist)
        db.commit()
        db.refresh(hist)
        return hist

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50) -> List[UploadHistory]:
        return db.query(UploadHistory).order_by(UploadHistory.created_at.desc()).offset(skip).limit(limit).all()
