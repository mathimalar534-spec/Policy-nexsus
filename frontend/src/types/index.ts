export interface User {
  id: number;
  username: string;
  email: string;
  role_name: string;
  is_active: boolean;
  created_at: string;
}

export interface PolicyMetadata {
  key: string;
  value: string;
}

export interface Policy {
  id: number;
  title: string;
  description?: string;
  file_path?: string;
  file_hash?: string;
  file_type?: string;
  status: 'active' | 'deprecated' | 'under_review';
  last_reviewed_at?: string;
  created_at: string;
  updated_at: string;
  author?: string;
  department?: string;
  version?: string;
  findings_count?: number;
  metadata_entries?: PolicyMetadata[];
}

export interface Obligation {
  id: number;
  policy_id: number;
  text_content: string;
  subject?: string;
  action?: string;
  object?: string;
  topic?: string;
  strength?: string;
  scope?: string;
  condition?: string;
  created_at: string;
}

export interface Finding {
  id: number;
  finding_type: 'CONFLICT' | 'REDUNDANCY' | 'STALE' | 'FALSE_POSITIVE_PRONE';
  finding_subtype: 'DIRECT_CONFLICT' | 'PARTIAL_CONFLICT' | 'REDUNDANCY' | 'STALE_POLICY' | 'STALE_REFERENCE' | 'FALSE_POSITIVE_PRONE';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  policy_a_id?: number;
  policy_b_id?: number;
  obligation_a_id?: number;
  obligation_b_id?: number;
  policy_id?: number;
  
  policy_a_title?: string;
  policy_b_title?: string;
  obligation_a_text?: string;
  obligation_b_text?: string;
  policy_title?: string;
  
  description: string;
  explanation?: string;
  recommendation?: string;
  created_at: string;
}

export interface Report {
  id: number;
  title: string;
  file_path?: string;
  type: 'PDF' | 'CSV' | 'JSON';
  summary?: string;
  status: 'Pending' | 'In Progress' | 'Completed' | 'Failed';
  created_at: string;
}

export interface DashboardSummary {
  total_policies: number;
  total_obligations: number;
  total_findings: number;
  active_conflicts: number;
  redundancies: number;
  stale_policies: number;
  stale_references: number;
  governance_score: number;
}

export interface ConflictMetric {
  policy_a: string;
  policy_b: string;
  subtype: string;
  severity: string;
  description: string;
}

export interface RedundancyMetric {
  policy_a: string;
  policy_b: string;
  description: string;
  explanation: string;
}

export interface StaleMetric {
  policy: string;
  subtype: string;
  last_reviewed?: string;
  description: string;
  explanation: string;
}

export interface Analytics {
  severity_distribution: Record<string, number>;
  subtype_distribution: Record<string, number>;
  department_distribution: Record<string, number>;
}

export interface ConfusionMatrix {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export interface EvaluationMetrics {
  precision: number;
  recall: number;
  accuracy: number;
  f1_score: number;
  confusion_matrix: ConfusionMatrix;
  total_ground_truth: number;
  total_detected: number;
}
