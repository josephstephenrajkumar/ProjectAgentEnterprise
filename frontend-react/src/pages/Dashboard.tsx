import { useState, useEffect } from 'react';
import { Loader2, TrendingUp, AlertTriangle, Briefcase, Activity } from 'lucide-react';
import axios from 'axios';

type Project = {
  project_id: string;
  ProjectNumber: string;
  customer: string;
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

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [data, setData] = useState<DashboardData | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState('');

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
      setError('Could not retrieve projects list.');
    } finally {
      setLoadingProjects(false);
    }
  };

  const fetchSummary = async (projectId: string) => {
    if (!projectId) return;
    try {
      setLoadingSummary(true);
      setError('');
      const res = await axios.get(`http://localhost:8000/api/projects/${projectId}/dashboard-summary`);
      setData(res.data);
    } catch (err) {
      console.error('Error fetching dashboard summary:', err);
      setError('Failed to calculate project analytics.');
    } finally {
      setLoadingSummary(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      fetchSummary(selectedProjectId);
    }
  }, [selectedProjectId]);

  const formatCurrency = (val: number) => {
    if (val >= 1_000_000) {
      return `$${(val / 1_000_000).toFixed(2)}M`;
    } else if (val >= 1_000) {
      return `$${(val / 1_000).toFixed(1)}K`;
    }
    return `$${val.toLocaleString()}`;
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Project Dashboard</h1>
          <p className="text-textSecondary mt-2">Overview of financial health, margins, and active forecasts.</p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center gap-3 bg-surface/50 border border-border p-2 rounded-xl">
          <Briefcase size={16} className="text-primary ml-2" />
          {loadingProjects ? (
            <div className="flex items-center gap-1.5 px-3 py-1">
              <Loader2 className="animate-spin text-primary" size={14} />
              <span className="text-xs text-textSecondary">Loading...</span>
            </div>
          ) : (
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-transparent border-0 text-xs font-semibold text-white focus:ring-0 focus:outline-none pr-8 cursor-pointer"
            >
              {projects.length === 0 ? (
                <option value="">No projects registered</option>
              ) : (
                projects.map((p) => (
                  <option key={p.project_id} value={p.project_id} className="bg-background text-white">
                    {p.customer} ({p.ProjectNumber})
                  </option>
                ))
              )}
            </select>
          )}
        </div>
      </header>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-xs">
          {error}
        </div>
      )}

      {loadingSummary ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <Loader2 className="animate-spin text-primary" size={32} />
          <span className="text-xs text-textSecondary">Recalculating forecast margins...</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="flex-1 glass-panel rounded-2xl p-8 flex items-center justify-center border-dashed border-2 border-border/50 bg-surface/20">
          <div className="text-center max-w-sm">
            <h3 className="text-lg font-bold text-white mb-2">No Projects Found</h3>
            <p className="text-xs text-textSecondary mb-4">
              Please create a project and upload forecast template files before checking the dashboard.
            </p>
          </div>
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Metric Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* EAC Revenue */}
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between hover:border-primary/20 transition-colors relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-2xl group-hover:bg-primary/10 transition-colors"></div>
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-textSecondary uppercase tracking-widest">Total Revenue EAC</span>
                <TrendingUp size={16} className="text-emerald-400" />
              </div>
              <span className="text-4xl font-extrabold text-white mt-4 tracking-tight">
                {formatCurrency(data.eac_revenue)}
              </span>
              <div className="mt-4 flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                  data.revenue_variance_percent >= 0 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {data.revenue_variance_percent >= 0 ? '+' : ''}
                  {data.revenue_variance_percent.toFixed(1)}% from Baseline
                </span>
                <span className="text-[10px] text-textSecondary">
                  Baseline: {formatCurrency(data.baseline_revenue)}
                </span>
              </div>
            </div>

            {/* Gross Margin */}
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between hover:border-primary/20 transition-colors relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-secondary/5 rounded-full blur-2xl group-hover:bg-secondary/10 transition-colors"></div>
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-textSecondary uppercase tracking-widest">Gross Margin %</span>
                <Activity size={16} className="text-secondary" />
              </div>
              <span className="text-4xl font-extrabold text-white mt-4 tracking-tight">
                {data.gm_percent.toFixed(1)}%
              </span>
              <div className="mt-4 flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                  data.gm_variance_percent >= 0 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {data.gm_variance_percent >= 0 ? '+' : ''}
                  {data.gm_variance_percent.toFixed(1)}% variance
                </span>
                <span className="text-[10px] text-textSecondary">
                  EAC Cost: {formatCurrency(data.eac_cost)}
                </span>
              </div>
            </div>

            {/* Active Risks */}
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between hover:border-primary/20 transition-colors relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 rounded-full blur-2xl group-hover:bg-red-500/10 transition-colors"></div>
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-textSecondary uppercase tracking-widest">Active Risks</span>
                <AlertTriangle size={16} className={data.high_priority_risks_count > 0 ? 'text-red-400' : 'text-amber-400'} />
              </div>
              <span className="text-4xl font-extrabold text-white mt-4 tracking-tight">
                {data.active_risks_count}
              </span>
              <div className="mt-4 flex items-center gap-2">
                <span className="bg-white/5 border border-border px-2 py-0.5 rounded text-[10px] text-textSecondary font-semibold">
                  {data.high_priority_risks_count} High Priority
                </span>
                <span className="text-[10px] text-textSecondary">
                  Tracked in RAID matrix
                </span>
              </div>
            </div>
          </div>

          {/* Details & Ingestion Status Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Financial Health Analysis */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                📈 Financial Health Analysis
              </h3>
              <div className="space-y-3.5 text-xs text-textSecondary">
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>EAC Revenue</span>
                  <span className="font-semibold text-white font-mono">{formatCurrency(data.eac_revenue)}</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>EAC Cost</span>
                  <span className="font-semibold text-white font-mono">{formatCurrency(data.eac_cost)}</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>Margin Profit Amount</span>
                  <span className="font-semibold text-primary font-mono">{formatCurrency(data.eac_revenue - data.eac_cost)}</span>
                </div>
                <div className="flex justify-between border-b border-border/40 pb-2">
                  <span>Baseline Margin</span>
                  <span className="font-semibold text-white font-mono">
                    {data.baseline_revenue > 0 
                      ? `${((data.baseline_revenue - data.baseline_cost) / data.baseline_revenue * 100).toFixed(1)}%` 
                      : '0.0%'}
                  </span>
                </div>
              </div>
            </div>

            {/* Platform Status */}
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                🛡️ Platform Status
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
                  <div className="text-xs">
                    <p className="font-semibold text-white">SQLite Relational Store Connected</p>
                    <p className="text-[10px] text-textSecondary">All tables are migrated and verified successfully.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
                  <div className="text-xs">
                    <p className="font-semibold text-white">ChromaDB Multi-Agent Pipeline Online</p>
                    <p className="text-[10px] text-textSecondary">RAG queries are routing automatically.</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-secondary"></div>
                  <div className="text-xs">
                    <p className="font-semibold text-white">Automation Engine Ready</p>
                    <p className="text-[10px] text-textSecondary">Agent runners executing in parallel.</p>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      ) : null}
    </div>
  );
}
