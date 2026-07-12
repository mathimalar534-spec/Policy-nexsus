from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # Admin, Auditor, Viewer
    permissions = Column(Text, nullable=True)

    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    policies = relationship("Policy", back_populates="owner")
    reports = relationship("Report", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True)
    file_type = Column(String(20), nullable=True)  # PDF, DOCX, TXT, MD
    status = Column(String(50), default="active")   # active, deprecated, under_review
    last_reviewed_at = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="policies")
    metadata_entries = relationship("PolicyMetadata", back_populates="policy", cascade="all, delete-orphan")
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="policy", cascade="all, delete-orphan")

class PolicyMetadata(Base):
    __tablename__ = "policy_metadata"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)

    policy = relationship("Policy", back_populates="metadata_entries")

class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    version_number = Column(String(50), nullable=False)
    text_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    policy = relationship("Policy", back_populates="versions")

class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    text_content = Column(Text, nullable=False)
    subject = Column(String(100), nullable=True)
    action = Column(String(100), nullable=True)
    object = Column(String(100), nullable=True)
    topic = Column(String(100), nullable=True)
    strength = Column(String(50), nullable=True)
    scope = Column(String(100), nullable=True)
    condition = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("Policy", back_populates="obligations")
    embeddings = relationship("Embedding", back_populates="obligation", cascade="all, delete-orphan")

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id"), nullable=False)
    vector = Column(JSON, nullable=False)  # Store embedding list of floats
    created_at = Column(DateTime, default=datetime.utcnow)

    obligation = relationship("Obligation", back_populates="embeddings")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    finding_type = Column(String(50), nullable=False)  # CONFLICT, REDUNDANCY, STALE, FALSE_POSITIVE_PRONE
    finding_subtype = Column(String(50), nullable=False)  # DIRECT_CONFLICT, PARTIAL_CONFLICT, REDUNDANCY, STALE_POLICY, STALE_REFERENCE, FALSE_POSITIVE_PRONE
    severity = Column(String(50), nullable=False)      # CRITICAL, HIGH, MEDIUM, LOW
    confidence = Column(Float, default=1.0)
    
    # Relationships for cross-policy conflicts
    policy_a_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    policy_b_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    obligation_a_id = Column(Integer, ForeignKey("obligations.id"), nullable=True)
    obligation_b_id = Column(Integer, ForeignKey("obligations.id"), nullable=True)

    # For single policy findings
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)

    description = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy_a = relationship("Policy", foreign_keys=[policy_a_id])
    policy_b = relationship("Policy", foreign_keys=[policy_b_id])
    obligation_a = relationship("Obligation", foreign_keys=[obligation_a_id])
    obligation_b = relationship("Obligation", foreign_keys=[obligation_b_id])
    policy = relationship("Policy", foreign_keys=[policy_id])

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=True)
    type = Column(String(20), nullable=False)  # PDF, CSV, JSON
    summary = Column(Text, nullable=True)
    status = Column(String(50), default="Pending")  # Pending, Completed, Failed
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    creator = relationship("User", back_populates="reports")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)  # Success, Error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
