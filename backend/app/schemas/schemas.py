from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role_name: str = "Viewer"  # Admin, Auditor, Viewer

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Policy Schemas
class PolicyMetadataSchema(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True

class PolicyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_type: Optional[str] = None
    status: str
    last_reviewed_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PolicyDetailResponse(PolicyResponse):
    metadata_entries: List[PolicyMetadataSchema] = []
    
    class Config:
        from_attributes = True

# Obligation Schemas
class ObligationResponse(BaseModel):
    id: int
    policy_id: int
    text_content: str
    subject: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    topic: Optional[str] = None
    strength: Optional[str] = None
    scope: Optional[str] = None
    condition: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Finding Schemas
class FindingResponse(BaseModel):
    id: int
    finding_type: str
    finding_subtype: str
    severity: str
    confidence: float
    policy_a_id: Optional[int] = None
    policy_b_id: Optional[int] = None
    obligation_a_id: Optional[int] = None
    obligation_b_id: Optional[int] = None
    policy_id: Optional[int] = None
    
    policy_a_title: Optional[str] = None
    policy_b_title: Optional[str] = None
    obligation_a_text: Optional[str] = None
    obligation_b_text: Optional[str] = None
    policy_title: Optional[str] = None
    
    description: str
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Report Schemas
class ReportResponse(BaseModel):
    id: int
    title: str
    file_path: Optional[str] = None
    type: str
    summary: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Dashboard / Analytics Schemas
class DashboardSummary(BaseModel):
    total_policies: int
    total_obligations: int
    total_findings: int
    active_conflicts: int
    redundancies: int
    stale_policies: int
    stale_references: int
    governance_score: float

class ConflictMetric(BaseModel):
    policy_a: str
    policy_b: str
    subtype: str
    severity: str
    description: str

class DashboardConflicts(BaseModel):
    conflicts: List[ConflictMetric]
    total: int

class RedundancyMetric(BaseModel):
    policy_a: str
    policy_b: str
    description: str
    explanation: str

class DashboardRedundancy(BaseModel):
    redundancies: List[RedundancyMetric]
    total: int

class StaleMetric(BaseModel):
    policy: str
    subtype: str
    last_reviewed: Optional[str] = None
    description: str
    explanation: str

class DashboardStale(BaseModel):
    stale_items: List[StaleMetric]
    total: int

class GovernanceScoreResponse(BaseModel):
    governance_score: float
    grade: str
    deductions: Dict[str, float]

# Evaluation Schemas
class ConfusionMatrixSchema(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int

class EvaluationResponse(BaseModel):
    precision: float
    recall: float
    accuracy: float
    f1_score: float
    confusion_matrix: ConfusionMatrixSchema
    total_ground_truth: int
    total_detected: int
