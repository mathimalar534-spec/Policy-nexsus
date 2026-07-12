import { 
  User, Policy, Obligation, Finding, Report, 
  DashboardSummary, ConflictMetric, RedundancyMetric, 
  StaleMetric, Analytics, EvaluationMetrics 
} from '../types';

const BASE_URL = '/api/v1';

function getHeaders() {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // Authentication
  async login(username: string, password: string): Promise<string> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to log in' }));
      throw new Error(err.detail || 'Login failed');
    }

    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    return data.access_token;
  },

  async register(username: string, email: string, password: string, role: string): Promise<User> {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
        role_name: role,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed');
    }

    return res.json();
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${BASE_URL}/auth/me`, {
      headers: getHeaders(),
    });
    if (!res.ok) {
      throw new Error('Not authenticated');
    }
    return res.json();
  },

  logout() {
    localStorage.removeItem('token');
  },

  // Policies
  async uploadPolicies(files: File[]): Promise<any> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await fetch(`${BASE_URL}/policies/upload`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to upload policies');
    }

    return res.json();
  },

  async comparePolicies(fileA: File, fileB: File): Promise<any> {
    const formData = new FormData();
    formData.append('file_a', fileA);
    formData.append('file_b', fileB);

    const res = await fetch(`${BASE_URL}/policies/compare`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to compare policies');
    }

    return res.json();
  },

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${BASE_URL}/dashboard/summary`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load dashboard summary');
    return res.json();
  },

  async getDashboardConflicts(): Promise<{ conflicts: ConflictMetric[]; total: number }> {
    const res = await fetch(`${BASE_URL}/dashboard/conflicts`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load conflicts');
    return res.json();
  },

  async getDashboardRedundancy(): Promise<{ redundancies: RedundancyMetric[]; total: number }> {
    const res = await fetch(`${BASE_URL}/dashboard/redundancy`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load redundancies');
    return res.json();
  },

  async getDashboardStale(): Promise<{ stale_items: StaleMetric[]; total: number }> {
    const res = await fetch(`${BASE_URL}/dashboard/stale`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load stale items');
    return res.json();
  },

  async getDashboardPolicies(): Promise<Policy[]> {
    const res = await fetch(`${BASE_URL}/dashboard/policies`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load policies list');
    return res.json();
  },

  async searchDashboard(params: Record<string, string>): Promise<Finding[]> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val) searchParams.append(key, val);
    });

    const res = await fetch(`${BASE_URL}/dashboard/search?${searchParams.toString()}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  },

  async getDashboardAnalytics(): Promise<Analytics> {
    const res = await fetch(`${BASE_URL}/dashboard/analytics`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load analytics');
    return res.json();
  },

  async getDashboardRiskScore(): Promise<{ governance_score: number; grade: string; deductions: Record<string, number> }> {
    const res = await fetch(`${BASE_URL}/dashboard/risk-score`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load risk score');
    return res.json();
  },

  // Dataset Operations
  async getDatasetStatistics(): Promise<any> {
    const res = await fetch(`${BASE_URL}/dataset/statistics`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load statistics');
    return res.json();
  },

  async getDatasetPolicies(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/dataset/policies`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load dataset policies');
    return res.json();
  },

  async getDatasetObligations(): Promise<Obligation[]> {
    const res = await fetch(`${BASE_URL}/dataset/obligations`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load obligations');
    return res.json();
  },

  async getDatasetFindings(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/dataset/findings`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load findings');
    return res.json();
  },

  async triggerReindex(): Promise<any> {
    const res = await fetch(`${BASE_URL}/dataset/reindex`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to reindex vector store');
    return res.json();
  },

  async triggerReload(): Promise<any> {
    const res = await fetch(`${BASE_URL}/dataset/reload`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to reload dataset');
    return res.json();
  },

  // Reports
  async listReports(): Promise<Report[]> {
    const res = await fetch(`${BASE_URL}/reports`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load reports');
    return res.json();
  },

  async createReport(title: string, formatType: string): Promise<Report> {
    const res = await fetch(`${BASE_URL}/reports?title=${encodeURIComponent(title)}&format_type=${formatType}`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to trigger report generation');
    return res.json();
  },

  async downloadReport(reportId: number): Promise<Blob> {
    const res = await fetch(`${BASE_URL}/reports/${reportId}/download`, {
      headers: getHeaders(),
    });
    if (!res.ok) {
      throw new Error('Failed to download report');
    }
    return res.blob();
  },

  // Evaluation
  async getEvaluationMetrics(): Promise<EvaluationMetrics> {
    const res = await fetch(`${BASE_URL}/evaluation`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to load evaluation metrics');
    return res.json();
  },
};
