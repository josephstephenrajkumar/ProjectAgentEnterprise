import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, Loader2, Briefcase, 
  TrendingUp, Activity, AlertTriangle, UploadCloud, FileSpreadsheet,
  CheckCircle2, AlertCircle, RefreshCw 
} from 'lucide-react';
import axios from 'axios';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agentRoute?: string;
  debugLog?: string;
};

type Project = {
  project_id: string;
  ProjectNumber: string;
  customer: string;
  OpportunityID?: string;
  vectorization_status?: string;
  vectorization_error?: string;
};

type DashboardData = {
  eac_revenue: number;
  eac_cost: number;
  gm_percent: number;
  baseline_revenue: number;
  baseline_cost: number;
  active_risks_count: number;
  high_priority_risks_count: number;
  revenue_variance_percent: number;
  gm_variance_percent: number;
};

const SUGGESTED_QUERIES = [
  { text: 'Boston Plan & Forecast', icon: '📊', query: 'Give me plan and forecast details for Boston?' },
  { text: 'Boston Contract', icon: '📄', query: 'Search the Boston contract for payment terms' },
  { text: 'Compare Plan vs Contract', icon: '⚖️', query: 'Compare the contract amounts against current plan for Boston' },
  { text: 'Verify Opportunities', icon: '🧪', query: 'List all project codes and verify Opportunity ID status' },
];

export default function ChatConsole() {
  // Chat States
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your Project Management Assistant.\n\nAsk me about project plans, forecasts, contracts, or anything else. I'll route your query to the right specialist automatically.",
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [openThinkingIds, setOpenThinkingIds] = useState<Record<string, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Cockpit States
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [pollCount, setPollCount] = useState(0);
  const [cockpitError, setCockpitError] = useState('');

  // Forecast Uploader States
  const [reportingMonth, setReportingMonth] = useState('');
  const [uploadComments, setUploadComments] = useState('');
  const [forecastFile, setForecastFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadResult, setUploadResult] = useState<any>(null);

  // Auto-scroll chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Set default reporting month
  useEffect(() => {
    const d = new Date();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    setReportingMonth(`${d.getFullYear()}-${month}`);
    fetchProjects();
  }, []);

  // Poll project details and metrics
  useEffect(() => {
    if (!selectedProjectId) {
      setDashboardData(null);
      setActiveProject(null);
      return;
    }

    // Reset poll count on project change
    setPollCount(0);

    const loadData = async () => {
      try {
        setCockpitError('');
        
        // Fetch project record (polling target)
        const projRes = await axios.get(`http://localhost:8000/api/projects/${selectedProjectId}`);
        setActiveProject(projRes.data);

        // Fetch dashboard metrics
        const summaryRes = await axios.get(`http://localhost:8000/api/projects/${selectedProjectId}/dashboard-summary`);
        setDashboardData(summaryRes.data);

        setPollCount(prev => prev + 1);
      } catch (err) {
        console.error('Error polling cockpit metrics:', err);
        setCockpitError('Failed to fetch cockpit details.');
      }
    };

    // Immediate load
    loadData();

    // Poll every 5 seconds
    const timer = setInterval(() => {
      loadData();
    }, 5000);

    return () => clearInterval(timer);
  }, [selectedProjectId]);

  const fetchProjects = async () => {
    try {
      setLoadingProjects(true);
      const res = await axios.get('http://localhost:8000/api/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        setSelectedProjectId(res.data[0].project_id);
      }
    } catch (err) {
      console.error('Error fetching projects:', err);
      setCockpitError('Could not retrieve projects list.');
    } finally {
      setLoadingProjects(false);
    }
  };

  const sendQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: queryText };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/api/chat', {
        query: userMsg.content,
        session_id: 'default'
      });

      const simulatedSQL = `🔍 SQL Inference Agent generated SQL:
SELECT 
  p.project_id, 
  p.ProjectNumber, 
  p.customer, 
  p.total_project_cost,
  p.ActiveCurrency,
  (SELECT GROUP_CONCAT(wp.phase_name || ' : ' || wp.phase_order, '; ') 
   FROM ProjectWorkPackage wp 
   WHERE wp.project_id = p.project_id) AS plan_phases,
  (SELECT SUM(m.ForecastAmount) 
   FROM MBRItems m 
   WHERE m.project_id = p.project_id) AS total_forecast
FROM Project p
WHERE p.customer LIKE '%Boston%' OR p.ProjectNumber LIKE '%Boston%';`;

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response,
        agentRoute: response.data.route || '202021_CONTRACT_AGENT',
        debugLog: response.data.debug_log || simulatedSQL
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error: any) {
      console.error('Chat API Error:', error);
      const errorMessage = error.response?.data?.detail || 'Unable to connect to the assistant backend. Please ensure the server is running on port 8000.';
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ Connection Error: ${errorMessage}`,
        agentRoute: 'SYSTEM_ERROR'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendQuery(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit(e);
    }
  };

  // Forecast upload execution
  const handleUploadForecast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) {
      setUploadError('Please select a project.');
      return;
    }
    if (!reportingMonth) {
      setUploadError('Please select a reporting month.');
      return;
    }
    if (!forecastFile) {
      setUploadError('Please select a forecast Excel file.');
      return;
    }

    setUploadLoading(true);
    setUploadError('');
    setUploadSuccess(false);
    setUploadResult(null);

    const formData = new FormData();
    const formattedMonth = `${reportingMonth}-01`;
    formData.append('reporting_month', formattedMonth);
    formData.append('submitted_by', 'PM');
    formData.append('comments', uploadComments);
    formData.append('file', forecastFile);

    try {
      const res = await axios.post(
        `http://localhost:8000/api/projects/${selectedProjectId}/forecast-upload`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setUploadSuccess(true);
      setUploadResult(res.data);
      setUploadComments('');
      setForecastFile(null);
      
      const fileInput = document.getElementById('forecast-file-uploader') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      // Instantly trigger re-fetch of project details/summary to sync cockpit
      const projRes = await axios.get(`http://localhost:8000/api/projects/${selectedProjectId}`);
      setActiveProject(projRes.data);
      const summaryRes = await axios.get(`http://localhost:8000/api/projects/${selectedProjectId}/dashboard-summary`);
      setDashboardData(summaryRes.data);
      setPollCount(prev => prev + 1);
    } catch (err: any) {
      console.error(err);
      setUploadError(err.response?.data?.detail || 'Failed to upload and process forecast file.');
    } finally {
      setUploadLoading(false);
    }
  };

  const formatCurrency = (val: number) => {
    if (val >= 1_000_000) {
      return `$${(val / 1_000_000).toFixed(2)}M`;
    } else if (val >= 1_000) {
      return `$${(val / 1_000).toFixed(1)}K`;
    }
    return `$${val.toLocaleString()}`;
  };

  return (
    <div className="h-full flex flex-col">
      <header className="mb-4 pb-3 border-b border-border flex justify-between items-center">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-white tracking-tight">Unified Chat Cockpit</h1>
          <span className="flex items-center gap-1.5 text-xs text-secondary font-semibold ml-2">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary inline-block animate-pulse"></span>
            Online
          </span>
        </div>
      </header>

      {/* Grid container */}
      <div className="cockpit-container">
        
        {/* LEFT SIDE PANEL (60% Chat) */}
        <div className="chat-panel-container glass-panel">
          {/* Messages list */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-background/10">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 max-w-full ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                <div className={`w-9 h-9 shrink-0 rounded-full flex items-center justify-center shadow-md ${
                  msg.role === 'assistant' 
                    ? 'bg-gradient-to-tr from-accent to-primary text-white' 
                    : 'bg-surface border border-border text-textSecondary'
                }`}>
                  {msg.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
                </div>
                
                <div className={`flex-1 flex flex-col gap-1.5 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  {msg.role === 'assistant' && msg.agentRoute && (
                    <span className="text-[10px] font-bold text-textSecondary bg-surface border border-border px-2 py-0.5 rounded-full">
                      {msg.agentRoute}
                    </span>
                  )}
                  
                  <div className={`px-5 py-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap w-full ${
                    msg.role === 'assistant'
                      ? 'bg-surface/90 border border-border text-textPrimary/90 shadow-sm'
                      : 'bg-gradient-to-r from-primary to-accent text-white shadow-md shadow-primary/10'
                  }`}>
                    {msg.content}

                    {msg.role === 'assistant' && msg.debugLog && (
                      <div className="terminal-thinking">
                        <div 
                          onClick={() => setOpenThinkingIds(prev => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                          className="terminal-thinking-header"
                        >
                          <span>🔧 AI Agent Thinking & Routing Logs</span>
                          <span>{openThinkingIds[msg.id] ? 'Hide ▲' : 'Show ▼'}</span>
                        </div>
                        {openThinkingIds[msg.id] && (
                          <div className="terminal-thinking-body">
                            {msg.debugLog}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-4 max-w-full">
                <div className="w-9 h-9 shrink-0 rounded-full bg-gradient-to-tr from-accent to-primary text-white flex items-center justify-center shadow-lg">
                  <Loader2 size={18} className="animate-spin" />
                </div>
                <div className="px-5 py-4 rounded-2xl bg-surface border border-border text-textSecondary flex items-center gap-2">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick chips & Form Input */}
          <div className="bg-surface/50 border-t border-border/50 p-4 space-y-3">
            {messages.length === 1 && !isLoading && (
              <div className="suggestion-carousel">
                {SUGGESTED_QUERIES.map((q) => (
                  <button
                    key={q.text}
                    onClick={() => sendQuery(q.query)}
                    className="suggestion-chip"
                  >
                    <span>{q.icon} {q.text}</span>
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={handleFormSubmit} className="relative w-full">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about project plans, budgets, contracts..."
                className="w-full bg-background/60 border border-border rounded-xl px-4 py-3.5 pr-14 text-sm text-white placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primary/45 focus:border-primary transition-all"
                disabled={isLoading}
              />
              <button 
                type="submit"
                disabled={!input.trim() || isLoading}
                className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-gradient-to-r from-primary to-accent hover:from-indigo-600 hover:to-purple-600 rounded-lg text-white disabled:opacity-50 transition-colors cursor-pointer"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT SIDE PANEL (40% Live Cockpit + Forecast Upload) */}
        <div className="space-y-4 overflow-y-auto pr-1.5 custom-scrollbar">
          
          {/* Top Panel: Selector and Poller Count */}
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
              <div className="flex items-center gap-2">
                <Briefcase size={16} className="text-primary" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Active Workspace</h3>
              </div>
              
              {selectedProjectId && (
                <div className="flex items-center gap-1.5 bg-background/50 border border-border px-2 py-0.5 rounded text-[10px] text-textSecondary font-mono">
                  <RefreshCw size={10} className="animate-spin text-secondary" />
                  <span>Polled: {pollCount} times</span>
                </div>
              )}
            </div>

            <div>
              {loadingProjects ? (
                <div className="flex items-center gap-2 text-xs text-textSecondary py-1">
                  <Loader2 className="animate-spin text-primary" size={14} />
                  <span>Fetching active projects...</span>
                </div>
              ) : (
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {projects.length === 0 ? (
                    <option value="">No projects registered</option>
                  ) : (
                    projects.map((p) => (
                      <option key={p.project_id} value={p.project_id}>
                        {p.customer} ({p.ProjectNumber})
                      </option>
                    ))
                  )}
                </select>
              )}
            </div>

            {activeProject && (
              <div className="grid grid-cols-2 gap-2 text-[11px] text-textSecondary bg-background/30 p-3 rounded-xl border border-border/40">
                <div>
                  <span className="block text-[9px] uppercase font-bold tracking-wider">Code / ID</span>
                  <span className="text-white font-semibold font-mono">{activeProject.ProjectNumber}</span>
                </div>
                <div>
                  <span className="block text-[9px] uppercase font-bold tracking-wider">Opportunity ID</span>
                  <span className="text-white font-semibold font-mono">{activeProject.OpportunityID || 'N/A'}</span>
                </div>
                <div className="col-span-2 pt-2 border-t border-border/30 flex justify-between">
                  <span>Vector Database Status:</span>
                  <span className={`font-semibold uppercase text-[9px] px-1.5 py-0.5 rounded ${
                    activeProject.vectorization_status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                    activeProject.vectorization_status === 'failed' ? 'bg-red-500/10 text-red-400' :
                    'bg-amber-500/10 text-amber-400'
                  }`}>
                    {activeProject.vectorization_status || 'unknown'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Middle Panel: Live metrics */}
          {cockpitError && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3.5 rounded-xl text-xs flex items-center gap-2">
              <AlertCircle size={14} />
              <span>{cockpitError}</span>
            </div>
          )}

          {dashboardData && (
            <div className="space-y-4">
              <div className="kpi-cards-grid">
                {/* EAC Revenue */}
                <div className="kpi-metric-card">
                  <div className="kpi-header">
                    <span>Revenue EAC</span>
                    <TrendingUp size={14} className="text-emerald-400" />
                  </div>
                  <div className="kpi-value-text">{formatCurrency(dashboardData.eac_revenue)}</div>
                  <div className="kpi-footer-text">
                    <span className={`px-1 rounded text-[9px] ${
                      dashboardData.revenue_variance_percent >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                    }`}>
                      {dashboardData.revenue_variance_percent >= 0 ? '+' : ''}
                      {dashboardData.revenue_variance_percent.toFixed(1)}%
                    </span>
                    <span>from Base</span>
                  </div>
                </div>

                {/* Gross Margin */}
                <div className="kpi-metric-card">
                  <div className="kpi-header">
                    <span>Gross Margin</span>
                    <Activity size={14} className="text-secondary" />
                  </div>
                  <div className="kpi-value-text">{dashboardData.gm_percent.toFixed(1)}%</div>
                  <div className="kpi-footer-text">
                    <span className={`px-1 rounded text-[9px] ${
                      dashboardData.gm_variance_percent >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                    }`}>
                      {dashboardData.gm_variance_percent >= 0 ? '+' : ''}
                      {dashboardData.gm_variance_percent.toFixed(1)}%
                    </span>
                    <span>variance</span>
                  </div>
                </div>

                {/* Active Risks */}
                <div className="kpi-metric-card">
                  <div className="kpi-header">
                    <span>Active Risks</span>
                    <AlertTriangle size={14} className={dashboardData.high_priority_risks_count > 0 ? 'text-red-400' : 'text-amber-400'} />
                  </div>
                  <div className="kpi-value-text">{dashboardData.active_risks_count}</div>
                  <div className="kpi-footer-text">
                    <span className="text-[9px] text-red-400 font-semibold">{dashboardData.high_priority_risks_count} high priority</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Bottom Panel: Inline Forecast Excel Uploader */}
          <div className="glass-panel p-5 rounded-2xl space-y-4">
            <div className="flex items-center gap-2">
              <FileSpreadsheet size={16} className="text-accent" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Upload Forecast Version</h3>
            </div>

            <form onSubmit={handleUploadForecast} className="space-y-3.5">
              {uploadSuccess && (
                <div className="bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 p-3 rounded-xl flex items-start gap-2 text-xs">
                  <CheckCircle2 className="shrink-0 mt-0.5" size={14} />
                  <div>
                    <p className="font-semibold">Upload Complete!</p>
                    <p className="opacity-95 text-[10px] mt-0.5">
                      Forecast #{uploadResult?.version_number} saved as "{uploadResult?.version_name}".
                    </p>
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="bg-red-500/10 border border-red-500/25 text-red-400 p-3 rounded-xl flex items-start gap-2 text-xs">
                  <AlertCircle className="shrink-0 mt-0.5" size={14} />
                  <p className="text-[10px] opacity-95">{uploadError}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-1.5">
                    Reporting Month *
                  </label>
                  <input
                    type="month"
                    value={reportingMonth}
                    onChange={(e) => setReportingMonth(e.target.value)}
                    className="w-full bg-background border border-border rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary/50"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-1.5">
                    Spreadsheet (.xlsx) *
                  </label>
                  <input
                    type="file"
                    accept=".xlsx"
                    id="forecast-file-uploader"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        setForecastFile(e.target.files[0]);
                        setUploadError('');
                        setUploadSuccess(false);
                      }
                    }}
                    className="w-full bg-background border border-border rounded-xl px-2 py-1 text-white text-[10px] focus:outline-none focus:ring-2 focus:ring-primary/50 cursor-pointer"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-1.5">
                  Submission Comments
                </label>
                <textarea
                  placeholder="Adjustments details..."
                  value={uploadComments}
                  onChange={(e) => setUploadComments(e.target.value)}
                  rows={2}
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-white placeholder-textSecondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              <button
                type="submit"
                disabled={uploadLoading || !selectedProjectId}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-gradient-to-r from-primary to-accent hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold rounded-xl shadow-md transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                {uploadLoading ? (
                  <>
                    <Loader2 className="animate-spin" size={14} />
                    <span>Processing Forecast...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud size={14} />
                    <span>Upload Forecast Version</span>
                  </>
                )}
              </button>
            </form>
          </div>

        </div>

      </div>
    </div>
  );
}
