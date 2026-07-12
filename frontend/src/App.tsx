import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, FileText, AlertTriangle, RefreshCw, 
  BarChart3, Download, Database, Settings as SettingsIcon, 
  LogOut, UploadCloud, CheckCircle2, Info, ShieldAlert, 
  Search, Filter, ArrowUpDown, User, Calendar, 
  Building, Clock, Plus, ChevronRight, FileJson, 
  TrendingDown, Activity, Check, AlertOctagon, HelpCircle
} from 'lucide-react';
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, 
  Tooltip, PieChart, Pie, Cell, Legend, LineChart, Line
} from 'recharts';
import { api } from './services/api';
import { 
  User as UserType, Policy, Finding, Obligation, 
  Report, DashboardSummary, ConflictMetric, 
  RedundancyMetric, StaleMetric, Analytics, EvaluationMetrics 
} from './types';

// Palette Colors
const COLORS = ['#2563EB', '#22C55E', '#F59E0B', '#DC2626', '#8B5CF6', '#EC4899'];

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserType | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('auditor');
  const [password, setPassword] = useState('auditorpassword');
  const [email, setEmail] = useState('auditor@example.com');
  const [role, setRole] = useState('Auditor');
  
  // Navigation State
  const [currentPage, setCurrentPage] = useState<string>('dashboard');
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  
  // Data State
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [conflicts, setConflicts] = useState<ConflictMetric[]>([]);
  const [redundancies, setRedundancies] = useState<RedundancyMetric[]>([]);
  const [staleItems, setStaleItems] = useState<StaleMetric[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationMetrics | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [obligations, setObligations] = useState<Obligation[]>([]);
  
  // Actions State
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  
  // Upload State
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done'>('idle');

  // Search/Filter Dashboard states
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSeverity, setSearchSeverity] = useState('');
  const [searchTopic, setSearchTopic] = useState('');
  const [searchDept, setSearchDept] = useState('');

  // Report Request states
  const [reportTitle, setReportTitle] = useState('Monthly Compliance Audit');
  const [reportFormat, setReportFormat] = useState('PDF');

  // Policy detail states
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [selectedPolicyObligations, setSelectedPolicyObligations] = useState<Obligation[]>([]);
  const [selectedPolicyFindings, setSelectedPolicyFindings] = useState<Finding[]>([]);

  // Check login status on load
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      loadUserProfile();
    }
  }, []);

  // Fetch dashboard data once logged in
  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated, currentPage]);

  const loadUserProfile = async () => {
    try {
      setLoading(true);
      const user = await api.getMe();
      setCurrentUser(user);
      setIsAuthenticated(true);
      setErrorMsg('');
    } catch (e: any) {
      api.logout();
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);
    try {
      await api.login(username, password);
      await loadUserProfile();
    } catch (e: any) {
      setErrorMsg(e.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);
    try {
      await api.register(username, email, password, role);
      setSuccessMsg('Account registered successfully! Please log in.');
      setAuthMode('login');
    } catch (e: any) {
      setErrorMsg(e.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [sumData, pols, confs, reds, stales, analData, reps, evalData, findList, obList] = await Promise.all([
        api.getDashboardSummary(),
        api.getDashboardPolicies(),
        api.getDashboardConflicts().then(r => r.conflicts),
        api.getDashboardRedundancy().then(r => r.redundancies),
        api.getDashboardStale().then(r => r.stale_items),
        api.getDashboardAnalytics(),
        api.listReports(),
        api.getEvaluationMetrics(),
        api.searchDashboard({}),
        api.getDatasetObligations()
      ]);
      
      setSummary(sumData);
      setPolicies(pols);
      setConflicts(confs);
      setRedundancies(reds);
      setStaleItems(stales);
      setAnalytics(analData);
      setReports(reps);
      setEvaluation(evalData);
      setFindings(findList);
      setObligations(obList);
    } catch (e: any) {
      setErrorMsg('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  // Load detailed policy data when viewed
  useEffect(() => {
    if (selectedPolicyId && isAuthenticated) {
      const pol = policies.find(p => p.id === selectedPolicyId);
      if (pol) {
        setSelectedPolicy(pol);
        // Filter obligations and findings for this policy
        const obs = obligations.filter(o => o.policy_id === selectedPolicyId);
        setSelectedPolicyObligations(obs);
        const finds = findings.filter(f => 
          f.policy_id === selectedPolicyId || 
          f.policy_a_id === selectedPolicyId || 
          f.policy_b_id === selectedPolicyId
        );
        setSelectedPolicyFindings(finds);
      }
    }
  }, [selectedPolicyId, policies, obligations, findings]);

  const handleLogout = () => {
    api.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setSummary(null);
  };

  // Dataset Operations
  const handleReloadDataset = async () => {
    if (!window.confirm("Reloading the dataset will clear all dynamic overrides and rebuild the PostgreSQL/FAISS repository. Do you want to proceed?")) {
      return;
    }
    try {
      setLoading(true);
      await api.triggerReload();
      setSuccessMsg('Dataset reload triggered in the background. Fresh values will appear in a few moments.');
      setTimeout(loadDashboardData, 3000);
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReindexFAISS = async () => {
    try {
      setLoading(true);
      const res = await api.triggerReindex();
      setSuccessMsg(`Reindexed successfully! Synchronized ${res.indexed_count} vectors.`);
      loadDashboardData();
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Reports
  const handleGenerateReport = async () => {
    try {
      setLoading(true);
      await api.createReport(reportTitle, reportFormat);
      setSuccessMsg(`Triggered report compilation. File type: ${reportFormat}.`);
      loadDashboardData();
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async (reportId: number, title: string, type: string) => {
    try {
      setLoading(true);
      const blob = await api.downloadReport(reportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.toLowerCase().replace(/ /g, '_')}_audit.${type.toLowerCase()}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e: any) {
      setErrorMsg('Failed to download report file.');
    } finally {
      setLoading(false);
    }
  };

  // File Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      const files = Array.from(e.dataTransfer.files);
      setUploadedFiles(prev => [...prev, ...files]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setUploadedFiles(prev => [...prev, ...files]);
    }
  };

  const removeUploadFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const triggerUpload = async () => {
    if (uploadedFiles.length === 0) return;
    setUploadStatus('uploading');
    setUploadProgress(20);
    try {
      await api.uploadPolicies(uploadedFiles);
      setUploadProgress(100);
      setUploadStatus('done');
      setUploadedFiles([]);
      setSuccessMsg('Upload completed! Conflict scan launched in the background.');
      setTimeout(() => {
        setUploadStatus('idle');
        setUploadProgress(0);
        loadDashboardData();
        setCurrentPage('dashboard');
      }, 1500);
    } catch (e: any) {
      setErrorMsg(e.message || 'File upload failed.');
      setUploadStatus('idle');
      setUploadProgress(0);
    }
  };

  // Exporters for dynamic search lists
  const handleExportCSV = () => {
    const headers = ['ID', 'Type', 'Subtype', 'Severity', 'Description', 'Created At'];
    const rows = findings.map(f => [
      f.id, f.finding_type, f.finding_subtype, f.severity, f.description, f.created_at
    ]);
    
    let csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(e => e.map(val => `"${val}"`).join(","))].join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "policy_findings_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-red-100 text-red-800 border border-red-200">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-orange-100 text-orange-800 border border-orange-200">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-amber-100 text-amber-800 border border-amber-200">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-blue-100 text-blue-800 border border-blue-200">LOW</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-green-500"></span>Active</span>;
      case 'deprecated':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"><span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-red-500"></span>Deprecated</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800"><span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-amber-500"></span>Under Review</span>;
    }
  };

  // Authentication Layout
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-blue-500" />
          <h2 className="mt-6 text-3xl font-extrabold text-white font-display">
            Centralized Policy Compliance Portal
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Enterprise Governance, Risk Management & Compliance Engine
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-slate-900 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-slate-800">
            {errorMsg && (
              <div className="mb-4 bg-red-900/30 border border-red-500 text-red-200 p-3 rounded text-sm">
                {errorMsg}
              </div>
            )}
            {successMsg && (
              <div className="mb-4 bg-green-900/30 border border-green-500 text-green-200 p-3 rounded text-sm">
                {successMsg}
              </div>
            )}

            {authMode === 'login' ? (
              <form className="space-y-6" onSubmit={handleLogin}>
                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Username
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    {loading ? 'Authenticating...' : 'Sign In'}
                  </button>
                </div>

                <div className="text-center mt-4">
                  <span className="text-sm text-slate-400">
                    Need Auditor Access?{' '}
                    <button
                      type="button"
                      onClick={() => setAuthMode('register')}
                      className="text-blue-500 hover:underline font-semibold"
                    >
                      Register Account
                    </button>
                  </span>
                </div>
              </form>
            ) : (
              <form className="space-y-6" onSubmit={handleRegister}>
                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Username
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300">
                    Assigned Role
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  >
                    <option value="Viewer">Viewer</option>
                    <option value="Auditor">Auditor</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    {loading ? 'Creating Account...' : 'Register'}
                  </button>
                </div>

                <div className="text-center mt-4">
                  <span className="text-sm text-slate-400">
                    Already registered?{' '}
                    <button
                      type="button"
                      onClick={() => setAuthMode('login')}
                      className="text-blue-500 hover:underline font-semibold"
                    >
                      Login Here
                    </button>
                  </span>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Aggregates for Recharts
  const severityChartData = analytics ? Object.entries(analytics.severity_distribution).map(([name, value]) => ({
    name, value
  })) : [];

  const deptChartData = analytics ? Object.entries(analytics.department_distribution).map(([name, value]) => ({
    name, value
  })) : [];

  const subtypeChartData = analytics ? Object.entries(analytics.subtype_distribution).map(([name, value]) => ({
    name, value
  })) : [];

  // Main Dashboard App Layout
  return (
    <div className="min-h-screen flex bg-slate-50 font-sans text-slate-900">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800">
        <div className="p-5 flex items-center gap-2 border-b border-slate-800">
          <ShieldAlert className="h-6 w-6 text-blue-500" />
          <span className="font-bold text-white tracking-tight font-display">Compliance Shield</span>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
            { id: 'policies', label: 'Policies List', icon: FileText },
            { id: 'upload', label: 'Upload Files', icon: UploadCloud },
            { id: 'conflicts', label: 'Conflicts View', icon: AlertOctagon },
            { id: 'redundancy', label: 'Redundancy List', icon: CopyIcon },
            { id: 'stale', label: 'Stale Checker', icon: Clock },
            { id: 'analytics', label: 'Risk Analytics', icon: BarChart3 },
            { id: 'reports', label: 'Report Generator', icon: Download },
            { id: 'dataset', label: 'Dataset Explorer', icon: Database },
            { id: 'settings', label: 'Settings', icon: SettingsIcon },
          ].map((item) => {
            const Icon = item.icon;
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setCurrentPage(item.id);
                  setSelectedPolicyId(null);
                  setSelectedFinding(null);
                  setErrorMsg('');
                  setSuccessMsg('');
                }}
                className={`w-full flex items-center px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  active 
                    ? 'bg-blue-600 text-white font-semibold' 
                    : 'hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className={`h-4.5 w-4.5 mr-3 ${active ? 'text-white' : 'text-slate-400'}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 flex flex-col gap-2 bg-slate-950/40">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 h-8 w-8 rounded-full flex items-center justify-center font-bold text-white text-sm">
              {currentUser?.username.substring(0,2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{currentUser?.username}</p>
              <p className="text-xs text-slate-400 truncate">{currentUser?.role_name} Mode</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-1.5 text-xs font-semibold rounded text-red-400 hover:bg-slate-800 border border-slate-800 transition-colors"
          >
            <LogOut className="h-3.5 w-3.5 mr-2" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        
        {/* Sticky Header */}
        <header className="sticky top-0 bg-white border-b border-slate-200 z-10 px-8 py-4 flex items-center justify-between shadow-sm">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight font-display">
              {currentPage.replace('-', ' ').toUpperCase()}
            </h1>
            <p className="text-xs text-slate-500">
              Central compliance logs & policy controls
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={loadDashboardData}
              disabled={loading}
              className="p-2 border border-slate-200 rounded hover:bg-slate-50 text-slate-600 disabled:opacity-50 transition-colors"
              title="Sync Repository"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <div className="text-xs font-medium text-slate-500">
              Local: {new Date().toLocaleDateString()}
            </div>
          </div>
        </header>

        {/* Dynamic Alerts Banner */}
        {successMsg && (
          <div className="mx-8 mt-4 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded text-sm flex items-center">
            <Check className="h-4 w-4 mr-2 text-green-500" />
            {successMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mx-8 mt-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded text-sm flex items-center">
            <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />
            {errorMsg}
          </div>
        )}

        {/* Content Area */}
        <main className="flex-1 p-8 overflow-y-auto">

          {/* PAGE: DASHBOARD */}
          {currentPage === 'dashboard' && !selectedPolicyId && (
            <div className="space-y-6">
              
              {/* KPI Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                  <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Total Policies</p>
                  <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{summary?.total_policies ?? 0}</p>
                  <p className="text-xs text-slate-500 mt-2">Active documents scanned</p>
                </div>

                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-red-500">
                  <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Active Conflicts</p>
                  <p className="mt-2 text-3xl font-extrabold text-red-600 font-display">{summary?.active_conflicts ?? 0}</p>
                  <p className="text-xs text-red-600/80 mt-2 flex items-center">
                    <AlertTriangle className="h-3 w-3 mr-1" /> Requires alignment
                  </p>
                </div>

                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-amber-500">
                  <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Stale Policies</p>
                  <p className="mt-2 text-3xl font-extrabold text-amber-600 font-display">{summary?.stale_policies ?? 0}</p>
                  <p className="text-xs text-slate-500 mt-2">Expired review limits</p>
                </div>

                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm border-l-4 border-l-blue-500">
                  <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Redundancies</p>
                  <p className="mt-2 text-3xl font-extrabold text-blue-600 font-display">{summary?.redundancies ?? 0}</p>
                  <p className="text-xs text-slate-500 mt-2">Overlapping statements</p>
                </div>

                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <p className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Governance Score</p>
                    <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{summary?.governance_score ?? 100}%</p>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
                    <div 
                      className={`h-1.5 rounded-full ${
                        (summary?.governance_score ?? 100) >= 80 ? 'bg-green-500' : (summary?.governance_score ?? 100) >= 60 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${summary?.governance_score ?? 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Chart 1: Severity distribution */}
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-4">Conflict Severity Breakdown</h3>
                  <div className="h-64">
                    {severityChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={severityChartData}>
                          <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
                          <YAxis stroke="#64748B" fontSize={12} />
                          <Tooltip />
                          <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]}>
                            {severityChartData.map((entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={
                                  entry.name === 'CRITICAL' || entry.name === 'HIGH' ? '#DC2626' : entry.name === 'MEDIUM' ? '#F59E0B' : '#2563EB'
                                } 
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-400 text-sm">No severity findings logged</div>
                    )}
                  </div>
                </div>

                {/* Chart 2: Department distribution */}
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-4">Violations by Department</h3>
                  <div className="h-64">
                    {deptChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={deptChartData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={80}
                            label={({name, percent}) => `${name} (${(percent*100).toFixed(0)}%)`}
                          >
                            {deptChartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-400 text-sm">No department data</div>
                    )}
                  </div>
                </div>
              </div>

              {/* Recent Policy Scan list */}
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900">Loaded Policies</h3>
                  <button 
                    onClick={() => setCurrentPage('policies')} 
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center"
                  >
                    View All <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 uppercase text-xs tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3">Policy Title</th>
                        <th className="px-6 py-3">Department</th>
                        <th className="px-6 py-3">Last Reviewed</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-center">Finding Counts</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {policies.slice(0, 5).map((pol) => {
                        const dept = metadataValue(pol, 'department') || 'General';
                        const reviewed = metadataValue(pol, 'last_reviewed') || 'Never';
                        return (
                          <tr 
                            key={pol.id} 
                            onClick={() => setSelectedPolicyId(pol.id)}
                            className="hover:bg-slate-50 cursor-pointer"
                          >
                            <td className="px-6 py-4 font-semibold text-slate-900">{pol.title}</td>
                            <td className="px-6 py-4">{dept}</td>
                            <td className="px-6 py-4">{reviewed}</td>
                            <td className="px-6 py-4">{getStatusBadge(pol.status)}</td>
                            <td className="px-6 py-4 text-center">
                              <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-800 bg-red-100 rounded-full border border-red-200">
                                {pol.findings_count ?? 0}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* PAGE: POLICIES LIST */}
          {currentPage === 'policies' && !selectedPolicyId && (
            <div className="space-y-6">
              <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                
                {/* Search / Filters */}
                <div className="flex flex-1 gap-3 w-full md:w-auto">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input 
                      type="text" 
                      placeholder="Search policy name..." 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <input 
                    type="text" 
                    placeholder="Dept..." 
                    value={searchDept}
                    onChange={(e) => setSearchDept(e.target.value)}
                    className="w-24 px-3 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="flex gap-2 w-full md:w-auto justify-end">
                  <button 
                    onClick={handleExportCSV}
                    className="flex items-center px-4 py-2 bg-slate-900 text-white rounded text-sm font-semibold hover:bg-slate-800 transition-colors"
                  >
                    <Download className="h-4 w-4 mr-2" /> Export CSV
                  </button>
                </div>
              </div>

              {/* Policies Grid */}
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">Title</th>
                      <th className="px-6 py-3">Version</th>
                      <th className="px-6 py-3">Author</th>
                      <th className="px-6 py-3">Department</th>
                      <th className="px-6 py-3">Last Reviewed</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3 text-center">Finding count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {policies
                      .filter(p => p.title.toLowerCase().includes(searchQuery.toLowerCase()))
                      .map((p) => {
                        const version = metadataValue(p, 'version') || '1.0';
                        const author = metadataValue(p, 'author') || 'Unknown';
                        const dept = metadataValue(p, 'department') || 'General';
                        const reviewed = metadataValue(p, 'last_reviewed') || 'Never';

                        return (
                          <tr 
                            key={p.id}
                            onClick={() => setSelectedPolicyId(p.id)}
                            className="hover:bg-slate-50 cursor-pointer"
                          >
                            <td className="px-6 py-4 font-semibold text-slate-950">{p.title}</td>
                            <td className="px-6 py-4">{version}</td>
                            <td className="px-6 py-4">{author}</td>
                            <td className="px-6 py-4">{dept}</td>
                            <td className="px-6 py-4">{reviewed}</td>
                            <td className="px-6 py-4">{getStatusBadge(p.status)}</td>
                            <td className="px-6 py-4 text-center">
                              <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold leading-none text-red-800 bg-red-100 border border-red-200">
                                {p.findings_count ?? 0}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* PAGE: POLICY DETAILS */}
          {selectedPolicyId && selectedPolicy && (
            <div className="space-y-6">
              
              {/* Back breadcrumb */}
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setSelectedPolicyId(null)}
                  className="text-xs font-bold text-blue-600 hover:underline"
                >
                  Policies
                </button>
                <ChevronRight className="h-3 w-3 text-slate-400" />
                <span className="text-xs text-slate-500 font-semibold">{selectedPolicy.title}</span>
              </div>

              {/* Policy Header Info */}
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 font-display">{selectedPolicy.title}</h2>
                  <p className="text-sm text-slate-500 mt-1">{selectedPolicy.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(selectedPolicy.status)}
                </div>
              </div>

              {/* Layout splits */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Details side bar */}
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-6">
                  <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">Policy Metadata</h3>
                  
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Department</span>
                      <span className="font-semibold">{metadataValue(selectedPolicy, 'department') || 'General'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Author</span>
                      <span className="font-semibold">{metadataValue(selectedPolicy, 'author') || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Current Version</span>
                      <span className="font-semibold bg-slate-100 px-2 py-0.5 rounded text-xs">{metadataValue(selectedPolicy, 'version') || '1.0'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Last Reviewed</span>
                      <span className="font-semibold">{metadataValue(selectedPolicy, 'last_reviewed') || 'Never'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">File Type</span>
                      <span className="font-semibold uppercase">{selectedPolicy.file_type}</span>
                    </div>
                  </div>
                </div>

                {/* Main obligations lists */}
                <div className="lg:col-span-2 space-y-6">
                  
                  {/* Obligations list */}
                  <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4">
                      Extracted Obligations ({selectedPolicyObligations.length})
                    </h3>
                    
                    <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                      {selectedPolicyObligations.map((ob, idx) => (
                        <div key={ob.id} className="p-3 bg-slate-50 rounded border border-slate-100 space-y-2">
                          <p className="text-sm text-slate-800 font-medium">
                            <span className="text-slate-400 mr-2">#{idx+1}</span>
                            {ob.text_content}
                          </p>
                          <div className="flex flex-wrap gap-2 text-[10px] font-semibold text-slate-500">
                            <span className="bg-slate-200/60 px-2 py-0.5 rounded uppercase">Topic: {ob.topic}</span>
                            <span className="bg-slate-200/60 px-2 py-0.5 rounded uppercase">Strength: {ob.strength}</span>
                            <span className="bg-slate-200/60 px-2 py-0.5 rounded uppercase">Scope: {ob.scope}</span>
                          </div>
                        </div>
                      ))}
                      {selectedPolicyObligations.length === 0 && (
                        <p className="text-sm text-slate-400 text-center py-6">No obligations extracted.</p>
                      )}
                    </div>
                  </div>

                  {/* Findings associated */}
                  <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4">
                      Compliance Findings ({selectedPolicyFindings.length})
                    </h3>

                    <div className="space-y-4">
                      {selectedPolicyFindings.map((find) => (
                        <div 
                          key={find.id} 
                          onClick={() => {
                            setSelectedFinding(find);
                            setCurrentPage('conflicts');
                          }}
                          className="p-4 bg-red-50/50 hover:bg-red-50 border border-red-100 rounded cursor-pointer transition-colors space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-red-800">{find.finding_subtype}</span>
                            {getSeverityBadge(find.severity)}
                          </div>
                          <p className="text-sm text-slate-950 font-medium">{find.description}</p>
                          <p className="text-xs text-slate-500">{find.explanation}</p>
                        </div>
                      ))}
                      {selectedPolicyFindings.length === 0 && (
                        <p className="text-sm text-slate-400 text-center py-6">No compliance violations detected.</p>
                      )}
                    </div>
                  </div>

                </div>
              </div>

            </div>
          )}

          {/* PAGE: CONFLICT VIEWER / LIST */}
          {currentPage === 'conflicts' && (
            <div className="space-y-6">
              
              {!selectedFinding ? (
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-200">
                    <h3 className="text-base font-bold text-slate-900">Identified Conflicts ({findings.filter(f=>f.finding_type==='CONFLICT').length})</h3>
                  </div>
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3">Policies Involved</th>
                        <th className="px-6 py-3">Conflict Type</th>
                        <th className="px-6 py-3">Severity</th>
                        <th className="px-6 py-3">Description</th>
                        <th className="px-6 py-3">Remediation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {findings
                        .filter(f => f.finding_type === 'CONFLICT' || f.finding_subtype === 'FALSE_POSITIVE_PRONE')
                        .map((f) => {
                          const polA = policies.find(p => p.id === f.policy_a_id);
                          const polB = policies.find(p => p.id === f.policy_b_id);
                          
                          return (
                            <tr 
                              key={f.id}
                              onClick={() => setSelectedFinding(f)}
                              className="hover:bg-slate-50 cursor-pointer"
                            >
                              <td className="px-6 py-4">
                                <span className="font-semibold text-slate-900">{polA?.title || 'Policy A'}</span>
                                <span className="text-slate-400 block text-xs">vs {polB?.title || 'Policy B'}</span>
                              </td>
                              <td className="px-6 py-4 font-medium">{f.finding_subtype}</td>
                              <td className="px-6 py-4">{getSeverityBadge(f.severity)}</td>
                              <td className="px-6 py-4 text-slate-700">{f.description}</td>
                              <td className="px-6 py-4 text-xs font-semibold text-blue-600 hover:underline">View details</td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="space-y-6">
                  
                  {/* Back button */}
                  <button 
                    onClick={() => setSelectedFinding(null)}
                    className="text-xs font-bold text-blue-600 hover:underline"
                  >
                    &larr; Back to conflicts list
                  </button>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    {/* Policy A Card */}
                    <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm relative border-t-4 border-t-slate-800">
                      <div className="absolute top-4 right-4 bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-bold">POLICY A</div>
                      <h4 className="text-lg font-bold text-slate-950 font-display">
                        {policies.find(p=>p.id===selectedFinding.policy_a_id)?.title || 'Policy A'}
                      </h4>
                      <p className="text-xs text-slate-400 mt-1">Department: {metadataValue(policies.find(p=>p.id===selectedFinding.policy_a_id) || null, 'department') || 'General'}</p>
                      
                      <div className="mt-6 p-4 bg-slate-50 border border-slate-100 rounded">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Conflicting Clause</p>
                        <p className="text-sm text-slate-950 mt-2 font-medium">
                          {selectedFinding.obligation_a_text || 'Obligation A statement details'}
                        </p>
                      </div>
                    </div>

                    {/* Policy B Card */}
                    <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm relative border-t-4 border-t-blue-600">
                      <div className="absolute top-4 right-4 bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-[10px] font-bold">POLICY B</div>
                      <h4 className="text-lg font-bold text-slate-950 font-display">
                        {policies.find(p=>p.id===selectedFinding.policy_b_id)?.title || 'Policy B'}
                      </h4>
                      <p className="text-xs text-slate-400 mt-1">Department: {metadataValue(policies.find(p=>p.id===selectedFinding.policy_b_id) || null, 'department') || 'General'}</p>
                      
                      <div className="mt-6 p-4 bg-blue-50/30 border border-blue-50 rounded">
                        <p className="text-xs font-semibold text-blue-400 uppercase tracking-wide">Conflicting Clause</p>
                        <p className="text-sm text-slate-950 mt-2 font-medium">
                          {selectedFinding.obligation_b_text || 'Obligation B statement details'}
                        </p>
                      </div>
                    </div>

                  </div>

                  {/* Conflict metrics detail */}
                  <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <div>
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit Evaluation</span>
                        <h3 className="text-base font-bold text-slate-950 mt-0.5">{selectedFinding.finding_subtype}</h3>
                      </div>
                      <div className="flex gap-3">
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Severity</span>
                          {getSeverityBadge(selectedFinding.severity)}
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Confidence</span>
                          <span className="text-xs font-semibold bg-slate-100 px-2 py-0.5 rounded">{selectedFinding.confidence * 100}%</span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                      <div>
                        <p className="font-bold text-slate-900">Explanation</p>
                        <p className="text-slate-600 mt-1 leading-relaxed">{selectedFinding.explanation}</p>
                      </div>
                      <div>
                        <p className="font-bold text-slate-900 text-red-600">Remediation Recommendation</p>
                        <p className="text-slate-600 mt-1 leading-relaxed">{selectedFinding.recommendation}</p>
                      </div>
                    </div>
                  </div>

                </div>
              )}

            </div>
          )}

          {/* PAGE: REDUNDANCY LIST */}
          {currentPage === 'redundancy' && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="text-base font-bold text-slate-900">Overlapping / Redundant Policies ({redundancies.length})</h3>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Policy A</th>
                    <th className="px-6 py-3">Policy B</th>
                    <th className="px-6 py-3">Scope Description</th>
                    <th className="px-6 py-3">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {redundancies.map((r, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-6 py-4 font-semibold text-slate-900">{r.policy_a}</td>
                      <td className="px-6 py-4 font-semibold text-slate-900">{r.policy_b}</td>
                      <td className="px-6 py-4 text-slate-700">{r.description}</td>
                      <td className="px-6 py-4 text-xs text-slate-500">{r.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* PAGE: STALE CHECKER */}
          {currentPage === 'stale' && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200">
                <h3 className="text-base font-bold text-slate-900">Stale Policies & Deprecated References ({staleItems.length})</h3>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3">Policy Document</th>
                    <th className="px-6 py-3">Violation Type</th>
                    <th className="px-6 py-3">Last Reviewed</th>
                    <th className="px-6 py-3">Scan Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {staleItems.map((s, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-6 py-4 font-semibold text-slate-900">{s.policy}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          s.subtype === 'STALE_POLICY' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                        }`}>
                          {s.subtype}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">{s.last_reviewed}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-800 text-xs">{s.description}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{s.explanation}</p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* PAGE: UPLOAD */}
          {currentPage === 'upload' && (
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg border border-slate-200 shadow-sm space-y-6">
              <div>
                <h3 className="text-lg font-bold text-slate-950 font-display">Ingest Policy Files</h3>
                <p className="text-sm text-slate-500 mt-1">Upload multiple documents (PDF, DOCX, TXT, MD) to run obligation mapping and conflict checkers.</p>
              </div>

              {/* Drag and Drop Zone */}
              <div 
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-all ${
                  isDragOver ? 'border-blue-500 bg-blue-50/20' : 'border-slate-300 hover:border-blue-400'
                }`}
              >
                <input 
                  type="file" 
                  multiple 
                  onChange={handleFileSelect} 
                  className="hidden" 
                  id="file-upload-input" 
                />
                <label htmlFor="file-upload-input" className="cursor-pointer">
                  <UploadCloud className="mx-auto h-12 w-12 text-slate-400" />
                  <p className="mt-2 text-sm font-semibold text-slate-900">Drag & drop files here, or <span className="text-blue-600 hover:underline">browse files</span></p>
                  <p className="text-xs text-slate-400 mt-1">Supported formats: PDF, DOCX, TXT, MD (Max 10MB per file)</p>
                </label>
              </div>

              {/* Uploading Progress Bar */}
              {uploadStatus === 'uploading' && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-semibold text-slate-500">
                    <span>Uploading and parsing policies...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                </div>
              )}

              {/* Preview Selected Files */}
              {uploadedFiles.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wide">Selected Files ({uploadedFiles.length})</p>
                  <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto pr-2 border border-slate-100 rounded">
                    {uploadedFiles.map((file, idx) => (
                      <div key={idx} className="flex justify-between items-center py-2 px-3 text-sm">
                        <span className="truncate font-semibold text-slate-800">{file.name}</span>
                        <button 
                          onClick={() => removeUploadFile(idx)} 
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                  
                  <button 
                    onClick={triggerUpload}
                    className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors shadow-sm"
                  >
                    Start Analysis Scan
                  </button>
                </div>
              )}

            </div>
          )}

          {/* PAGE: RISK ANALYTICS */}
          {currentPage === 'analytics' && (
            <div className="space-y-6">
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Severity Breakdown */}
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-4">Findings Severity Chart</h3>
                  <div className="h-64">
                    {severityChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={severityChartData}>
                          <XAxis dataKey="name" stroke="#64748B" fontSize={11} />
                          <YAxis stroke="#64748B" fontSize={11} />
                          <Tooltip />
                          <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-400">No findings logged</div>
                    )}
                  </div>
                </div>

                {/* Subtype Breakdown */}
                <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-4">Violations by Action Subtype</h3>
                  <div className="h-64">
                    {subtypeChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={subtypeChartData} layout="vertical">
                          <XAxis type="number" stroke="#64748B" fontSize={11} />
                          <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={10} width={120} />
                          <Tooltip />
                          <Bar dataKey="value" fill="#8B5CF6" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-400">No subtype data</div>
                    )}
                  </div>
                </div>

              </div>

              {/* Evaluation ground truth metrics dashboard */}
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 border-b border-slate-100 pb-3 mb-6">
                  <Activity className="h-5 w-5 text-blue-500" />
                  <h3 className="text-base font-bold text-slate-900">NLP Conflict Engine Model Evaluation</h3>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="bg-slate-50 p-4 rounded border border-slate-100 text-center">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Accuracy</p>
                    <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{evaluation ? `${(evaluation.accuracy * 100).toFixed(1)}%` : '0%'}</p>
                  </div>
                  <div className="bg-slate-50 p-4 rounded border border-slate-100 text-center">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Precision</p>
                    <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{evaluation ? `${(evaluation.precision * 100).toFixed(1)}%` : '0%'}</p>
                  </div>
                  <div className="bg-slate-50 p-4 rounded border border-slate-100 text-center">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Recall</p>
                    <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{evaluation ? `${(evaluation.recall * 100).toFixed(1)}%` : '0%'}</p>
                  </div>
                  <div className="bg-slate-50 p-4 rounded border border-slate-100 text-center">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">F1 Score</p>
                    <p className="mt-2 text-3xl font-extrabold text-slate-900 font-display">{evaluation ? `${(evaluation.f1_score * 100).toFixed(1)}%` : '0%'}</p>
                  </div>
                </div>

                {/* Confusion matrix grid */}
                <div className="mt-8 max-w-md mx-auto">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider text-center mb-4">Confusion Matrix</h4>
                  <div className="grid grid-cols-2 gap-2 text-center text-sm font-semibold">
                    <div className="bg-green-50 border border-green-200 p-4 rounded">
                      <span className="text-xs text-green-700 block uppercase">True Positives (TP)</span>
                      <span className="text-2xl font-extrabold text-green-900 mt-1 block">{evaluation?.confusion_matrix.tp ?? 0}</span>
                    </div>
                    <div className="bg-red-50 border border-red-200 p-4 rounded">
                      <span className="text-xs text-red-700 block uppercase">False Positives (FP)</span>
                      <span className="text-2xl font-extrabold text-red-900 mt-1 block">{evaluation?.confusion_matrix.fp ?? 0}</span>
                    </div>
                    <div className="bg-orange-50 border border-orange-200 p-4 rounded">
                      <span className="text-xs text-orange-700 block uppercase">False Negatives (FN)</span>
                      <span className="text-2xl font-extrabold text-orange-900 mt-1 block">{evaluation?.confusion_matrix.fn ?? 0}</span>
                    </div>
                    <div className="bg-slate-100 border border-slate-200 p-4 rounded">
                      <span className="text-xs text-slate-600 block uppercase">True Negatives (TN)</span>
                      <span className="text-2xl font-extrabold text-slate-900 mt-1 block">{evaluation?.confusion_matrix.tn ?? 0}</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* PAGE: REPORT GENERATOR */}
          {currentPage === 'reports' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Creator form */}
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
                <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">Compile Audit Report</h3>
                
                <div className="space-y-4 text-sm">
                  <div>
                    <label className="block font-medium text-slate-700">Report Title</label>
                    <input 
                      type="text" 
                      value={reportTitle}
                      onChange={(e) => setReportTitle(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block font-medium text-slate-700">Export Format</label>
                    <select 
                      value={reportFormat} 
                      onChange={(e) => setReportFormat(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="PDF">PDF Document (ReportLab Layout)</option>
                      <option value="CSV">CSV Spreadsheet</option>
                      <option value="JSON">Raw JSON Output</option>
                    </select>
                  </div>

                  <button 
                    onClick={handleGenerateReport}
                    className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors shadow-sm"
                  >
                    Compile Report
                  </button>
                </div>
              </div>

              {/* Reports list */}
              <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-900">Audit Reports History</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3">Report Name</th>
                        <th className="px-6 py-3">Format</th>
                        <th className="px-6 py-3">Date</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3 text-right">Downloads</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {reports.map((rep) => (
                        <tr key={rep.id}>
                          <td className="px-6 py-4">
                            <span className="font-semibold text-slate-900 block">{rep.title}</span>
                            <span className="text-xs text-slate-400 block truncate max-w-sm">{rep.summary || 'Awaiting compile...'}</span>
                          </td>
                          <td className="px-6 py-4 font-mono text-xs">{rep.type}</td>
                          <td className="px-6 py-4 text-xs">{new Date(rep.created_at).toLocaleDateString()}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              rep.status === 'Completed' ? 'bg-green-100 text-green-800' : rep.status === 'Failed' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                            }`}>
                              {rep.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            {rep.status === 'Completed' && (
                              <button 
                                onClick={() => handleDownloadReport(rep.id, rep.title, rep.type)}
                                className="inline-flex items-center px-2.5 py-1.5 border border-slate-200 rounded text-xs font-semibold hover:bg-slate-50 transition-colors"
                              >
                                <Download className="h-3 w-3 mr-1" /> Download
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* PAGE: DATASET EXPLORER */}
          {currentPage === 'dataset' && (
            <div className="space-y-6">
              
              {/* Trigger configs card */}
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-950 font-display">Seeded Dataset Controls</h3>
                  <p className="text-sm text-slate-500 mt-1">Configure vector indices, load/rebuild ground truth datasets, or flush test caches.</p>
                </div>
                <div className="flex gap-3">
                  <button 
                    onClick={handleReindexFAISS}
                    className="flex items-center px-4 py-2 border border-slate-200 rounded text-sm font-semibold hover:bg-slate-50 transition-colors"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" /> Reindex FAISS
                  </button>
                  <button 
                    onClick={handleReloadDataset}
                    className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold transition-colors shadow-sm"
                  >
                    <Trash2Icon className="h-4 w-4 mr-2" /> Wipe & Reset DB
                  </button>
                </div>
              </div>

              {/* Obligations grid */}
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-900">Seeded Obligations Registry ({obligations.length})</h3>
                </div>
                <div className="max-h-[500px] overflow-y-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500 uppercase text-xs border-b border-slate-200 sticky top-0">
                      <tr>
                        <th className="px-6 py-3">Topic</th>
                        <th className="px-6 py-3">Strength</th>
                        <th className="px-6 py-3">Target Scope</th>
                        <th className="px-6 py-3">Extracted Text</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {obligations.map((ob) => (
                        <tr key={ob.id}>
                          <td className="px-6 py-4 font-semibold text-slate-900">{ob.topic}</td>
                          <td className="px-6 py-4 font-mono text-xs">{ob.strength}</td>
                          <td className="px-6 py-4">{ob.scope}</td>
                          <td className="px-6 py-4 text-xs font-mono text-slate-600">{ob.text_content}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* PAGE: SETTINGS */}
          {currentPage === 'settings' && (
            <div className="max-w-xl mx-auto bg-white p-8 rounded-lg border border-slate-200 shadow-sm space-y-6">
              <h3 className="text-lg font-bold text-slate-950 font-display border-b border-slate-100 pb-3">Security & Threshold Controls</h3>
              
              <div className="space-y-4 text-sm">
                <div>
                  <label className="block font-medium text-slate-700">Policy Reviewed Threshold (Days)</label>
                  <input 
                    type="number" 
                    defaultValue="365"
                    className="mt-1 block w-full px-3 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-400 mt-1">If a policy has not been reviewed within these days, it will be flagged as STALE_POLICY.</p>
                </div>

                <div>
                  <label className="block font-medium text-slate-700">Vector Search Match Limit (K)</label>
                  <input 
                    type="number" 
                    defaultValue="5"
                    className="mt-1 block w-full px-3 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="bg-slate-50 p-4 rounded border border-slate-200/60">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">Deprecated Security Terms Scanned</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {['SHA1', 'DES', 'FTP', 'TLS1.0', 'SSL', 'Windows Server 2012', 'WEP', '3DES', 'MD5'].map(t => (
                      <span key={t} className="bg-white border border-slate-200 px-2 py-0.5 rounded text-xs text-slate-700">{t}</span>
                    ))}
                  </div>
                </div>

                <button 
                  onClick={() => setSuccessMsg('Settings updated successfully.')}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors shadow-sm"
                >
                  Save Configuration
                </button>
              </div>
            </div>
          )}

        </main>
      </div>

    </div>
  );
}

// Helpers
function metadataValue(policy: Policy | null, key: string): string {
  if (!policy || !policy.metadata_entries) return '';
  const match = policy.metadata_entries.find(m => m.key === key);
  return match ? match.value : '';
}

// Subcomponents wrappers since we are not using separate files for compilation ease inside sandbox
function CopyIcon(props: any) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={props.className}
    >
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  );
}

function Trash2Icon(props: any) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={props.className}
    >
      <path d="M3 6h18" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  );
}
