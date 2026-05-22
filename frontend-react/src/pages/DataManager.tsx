import { useState, useEffect } from 'react';
import { Search, Trash2, Info, Loader2, Database, RefreshCw, Zap, Layers } from 'lucide-react';
import axios from 'axios';

type ProjectData = {
  project_id: string;
  ProjectNumber: string;
  OpportunityID: string;
  customer: string;
  end_customer?: string;
  PMName?: string;
  DMName?: string;
  country?: string;
  startdateContract?: string;
  endDateContract?: string;
  current_version_name?: string;
  current_version_status?: string;
  reporting_month?: string;
};

type KuzuStatus = {
  status: string;
  message: string;
  counts: {
    Project: number;
    Resource: number;
    Milestone: number;
    RAIDItem: number;
  };
};

export default function DataManager() {
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [selectedTable, setSelectedTable] = useState('Project');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [projectToDrop, setProjectToDrop] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [feedbackMessage, setFeedbackMessage] = useState('');

  // KuzuDB Co-existence States
  const [kuzuStatus, setKuzuStatus] = useState<KuzuStatus | null>(null);
  const [kuzuLoading, setKuzuLoading] = useState(false);
  const [kuzuActionMessage, setKuzuActionMessage] = useState('');

  // E2E Testing States
  const [testRunning, setTestRunning] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const fetchProjects = async () => {
    try {
      setFetching(true);
      const res = await axios.get('http://localhost:8000/api/projects');
      setProjects(res.data);
    } catch (err) {
      console.error('Error fetching projects:', err);
      setFeedbackMessage('Failed to fetch projects from database.');
    } finally {
      setFetching(false);
    }
  };

  const fetchKuzuStatus = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/projects/kuzudb/status');
      setKuzuStatus(res.data);
    } catch (err) {
      console.error('Error fetching KuzuDB status:', err);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchKuzuStatus();
  }, []);

  useEffect(() => {
    let interval: any;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchProjects();
        fetchKuzuStatus();
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleDropProject = async () => {
    if (!projectToDrop) return;
    const targetProject = projects.find(p => p.project_id === projectToDrop);
    const label = targetProject ? `${targetProject.customer} (${targetProject.ProjectNumber})` : projectToDrop;

    if (!window.confirm(`Are you sure you want to permanently delete the project "${label}"? This will delete all planning versions, resources, milestones, RAG vector spaces, and files.`)) {
      return;
    }

    setLoading(true);
    try {
      const res = await axios.delete(`http://localhost:8000/api/projects/${projectToDrop}`);
      setFeedbackMessage(res.data.message || `Successfully dropped project: ${label}`);
      setProjectToDrop('');
      fetchProjects();
      // Auto refresh KuzuDB status since deleting a project cascades there too
      await fetchKuzuStatus();
    } catch (err: any) {
      console.error(err);
      setFeedbackMessage(err.response?.data?.detail || `Failed to drop project: ${label}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRecreateKuzu = async () => {
    if (!window.confirm("Are you sure you want to delete and recreate the KuzuDB graph database projection? This will wipe the current graph directory and rebuild it by extracting all current projects, milestones, resources, and RAID items from SQLite.")) {
      return;
    }
    setKuzuLoading(true);
    setKuzuActionMessage('');
    try {
      const res = await axios.post('http://localhost:8000/api/projects/kuzudb/recreate');
      setKuzuActionMessage(res.data.message || 'KuzuDB database successfully re-created!');
      await fetchKuzuStatus();
    } catch (err: any) {
      console.error('Error recreating KuzuDB:', err);
      setKuzuActionMessage(err.response?.data?.detail || 'Failed to re-create KuzuDB.');
    } finally {
      setKuzuLoading(false);
    }
  };

  const handleRunTests = async () => {
    setTestRunning(true);
    setTestError(null);
    setTestResults(null);
    try {
      const res = await axios.post('http://localhost:8000/api/projects/test/run');
      setTestResults(res.data);
      // Auto-refresh tables and Kuzu graph counts
      fetchProjects();
      fetchKuzuStatus();
    } catch (err: any) {
      console.error('Error running E2E tests:', err);
      setTestError(err.response?.data?.detail || 'Failed to execute E2E tests.');
    } finally {
      setTestRunning(false);
    }
  };

  const filteredData = projects.filter(row => 
    Object.values(row).some(val => 
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            🔀 Database Co-existence Manager
          </h1>
          <p className="text-textSecondary mt-2">Manage the SQLite master system of record and the KuzuDB graph read projection (CQRS).</p>
        </div>
      </header>

      {/* CQRS Co-existence Model Control Center */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SQL System of Record */}
        <div className="glass-panel rounded-2xl p-6 border border-white/5 shadow-2xl flex flex-col justify-between space-y-4 hover:border-primary/20 transition-all duration-300">
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <Database size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Write Master (SSOT)</h3>
                <span className="text-[10px] text-primary font-semibold font-mono">SQLite Relational DB</span>
              </div>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed">
              Acts as the absolute single source of truth for transactions. All planning versions, EAC forecasts, resource allocations, and RAID logs are saved here first to ensure strict relational integrity.
            </p>
          </div>
          <div className="pt-2 flex items-center justify-between border-t border-border">
            <span className="text-xs text-textSecondary">Relational Tables</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Active / Master
            </span>
          </div>
        </div>

        {/* Sync & Rebuild Actions */}
        <div className="glass-panel rounded-2xl p-6 border border-white/5 shadow-2xl flex flex-col justify-between space-y-4 hover:border-accent/20 transition-all duration-300">
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-accent/10 rounded-lg text-accent">
                <Zap size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Replication Sync</h3>
                <span className="text-[10px] text-accent font-semibold font-mono">Dual-Write Ingestion Hooks</span>
              </div>
            </div>
            <p className="text-xs text-textSecondary leading-relaxed">
              Synchronizes SQLite records to KuzuDB automatically on project ingest or delete. If data becomes inconsistent, click below to wipe the graph projection and reconstruct it entirely.
            </p>
          </div>
          <div className="pt-2 flex flex-col gap-2 border-t border-border">
            <button
              onClick={handleRecreateKuzu}
              disabled={kuzuLoading}
              className="w-full py-2 bg-accent hover:bg-violet-600 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition-all active:scale-95 flex items-center justify-center gap-2 hover:shadow-lg hover:shadow-accent/25"
            >
              {kuzuLoading ? (
                <>
                  <Loader2 className="animate-spin" size={14} />
                  <span>Reconstructing Graph...</span>
                </>
              ) : (
                <>
                  <RefreshCw size={14} className={kuzuLoading ? 'animate-spin' : ''} />
                  <span>Recreate Graph Projection</span>
                </>
              )}
            </button>
            {kuzuActionMessage && (
              <div className="text-[10px] font-mono text-center text-textSecondary max-w-full truncate" title={kuzuActionMessage}>
                {kuzuActionMessage}
              </div>
            )}
          </div>
        </div>

        {/* Graph Read Projection */}
        <div className="glass-panel rounded-2xl p-6 border border-white/5 shadow-2xl flex flex-col justify-between space-y-4 hover:border-secondary/20 transition-all duration-300">
          <div className="space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-secondary/10 rounded-lg text-secondary">
                <Layers size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Read Projection</h3>
                <span className="text-[10px] text-secondary font-semibold font-mono">KuzuDB Property Graph</span>
              </div>
            </div>
            
            {/* Status Indicator */}
            {kuzuStatus ? (
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-textSecondary">Graph Status:</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  kuzuStatus.status === 'ready' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  kuzuStatus.status === 'unavailable' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}>
                  {kuzuStatus.status}
                </span>
              </div>
            ) : (
              <div className="flex justify-center py-2">
                <Loader2 className="animate-spin text-textSecondary" size={16} />
              </div>
            )}

            {/* Counts */}
            {kuzuStatus?.status === 'ready' && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div className="bg-background/50 border border-border rounded-xl p-2 text-center">
                  <div className="text-textSecondary text-[9px] uppercase font-bold tracking-wider font-mono">Projects</div>
                  <div className="text-sm font-bold text-primary">{kuzuStatus.counts.Project}</div>
                </div>
                <div className="bg-background/50 border border-border rounded-xl p-2 text-center">
                  <div className="text-textSecondary text-[9px] uppercase font-bold tracking-wider font-mono">Milestones</div>
                  <div className="text-sm font-bold text-accent">{kuzuStatus.counts.Milestone}</div>
                </div>
                <div className="bg-background/50 border border-border rounded-xl p-2 text-center">
                  <div className="text-textSecondary text-[9px] uppercase font-bold tracking-wider font-mono">Resources</div>
                  <div className="text-sm font-bold text-secondary">{kuzuStatus.counts.Resource}</div>
                </div>
                <div className="bg-background/50 border border-border rounded-xl p-2 text-center">
                  <div className="text-textSecondary text-[9px] uppercase font-bold tracking-wider font-mono">RAID Items</div>
                  <div className="text-sm font-bold text-amber-400">{kuzuStatus.counts.RAIDItem}</div>
                </div>
              </div>
            )}
            
            {kuzuStatus?.status === 'ready' && (
              <p className="text-[10px] text-textSecondary leading-normal text-center italic">
                Pointers link adjacent entities in memory for microsecond traversals.
              </p>
            )}
          </div>
        </div>
      </div>


      {/* Main Manager Panel */}
      <div className="glass-panel rounded-2xl p-6 shadow-2xl space-y-6">
        
        {/* Controls */}
        <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
          <div className="flex items-center gap-4 w-full md:w-auto">
            <select
              value={selectedTable}
              onChange={(e) => setSelectedTable(e.target.value)}
              className="bg-background border border-border rounded-xl px-4 py-2.5 text-white font-medium focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="Project">Project Table</option>
            </select>

            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-textSecondary select-none">
              <input 
                type="checkbox" 
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 rounded border-border bg-background checked:bg-primary" 
              />
              Auto-Refresh (5s)
            </label>

            <button
              onClick={fetchProjects}
              className="px-3 py-1.5 bg-surface hover:bg-white/5 border border-border text-white text-xs font-medium rounded-lg transition-all active:scale-95"
            >
              Reload
            </button>
          </div>

          <div className="relative w-full md:w-64">
            <input
              type="text"
              placeholder="Search in table..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-background border border-border rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <Search className="absolute left-3.5 top-2.5 text-textSecondary" size={14} />
          </div>
        </div>

        {/* Informative Tip */}
        <div className="bg-primary/5 border border-primary/20 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-textSecondary">
          <Info className="shrink-0 text-primary mt-0.5" size={16} />
          <div>
            <span className="font-semibold text-primary">Dynamic Inference Tip:</span> All projects created from the Create Project screen or imported via SQL are registered below. Dropping a project cascades and deletes all related metrics and forecast records automatically.
          </div>
        </div>

        {/* Database Table */}
        <div className="overflow-x-auto border border-border rounded-xl bg-background/50">
          {fetching && projects.length === 0 ? (
            <div className="p-8 text-center flex justify-center items-center gap-2">
              <Loader2 className="animate-spin text-primary" size={18} />
              <span className="text-textSecondary text-xs">Loading database records...</span>
            </div>
          ) : (
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-background/80 text-textSecondary uppercase tracking-wider font-semibold">
                  <th className="p-4">Project ID</th>
                  <th className="p-4">Project Code</th>
                  <th className="p-4">Customer / Name</th>
                  <th className="p-4">Opportunity ID</th>
                  <th className="p-4">Stage</th>
                  <th className="p-4">PM Name</th>
                  <th className="p-4">DM Name</th>
                  <th className="p-4">Current Version</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Reporting Month</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-textPrimary/90">
                {filteredData.length > 0 ? (
                  filteredData.map((row) => (
                    <tr key={row.project_id} className="hover:bg-white/5 transition-colors">
                      <td className="p-4 font-mono text-[10px] text-textSecondary max-w-[120px] truncate" title={row.project_id}>
                        {row.project_id}
                      </td>
                      <td className="p-4 font-semibold text-primary">{row.ProjectNumber}</td>
                      <td className="p-4 font-medium">{row.customer}</td>
                      <td className="p-4 font-mono">{row.OpportunityID || 'N/A'}</td>
                      <td className="p-4">
                        <span className="px-2 py-0.5 rounded bg-surface border border-border text-[10px]">
                          {row.end_customer || 'Open'}
                        </span>
                      </td>
                      <td className="p-4">{row.PMName || 'system'}</td>
                      <td className="p-4">{row.DMName || 'system'}</td>
                      <td className="p-4 font-semibold text-secondary">{row.current_version_name || 'None'}</td>
                      <td className="p-4">
                        {row.current_version_status ? (
                          <span className={`px-2 py-0.5 rounded text-[10px] ${
                            row.current_version_status === 'Approved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25' :
                            row.current_version_status === 'Submitted' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/25' :
                            'bg-surface border border-border text-textSecondary'
                          }`}>
                            {row.current_version_status}
                          </span>
                        ) : (
                          <span className="text-textSecondary">-</span>
                        )}
                      </td>
                      <td className="p-4 font-mono">{row.reporting_month || '-'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={10} className="p-8 text-center text-textSecondary">
                      No records found matching the query.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* System Verification & E2E Testing */}
      <div className="glass-panel rounded-2xl p-6 border border-white/5 shadow-2xl space-y-6 hover:border-primary/10 transition-all duration-300">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              🧪 System Verification & E2E Testing
            </h3>
            <p className="text-xs text-textSecondary">
              Run automated scripts to verify project ingestion, database schema creation, vectorization, and LangGraph chat routing logic.
            </p>
          </div>
          <button
            onClick={handleRunTests}
            disabled={testRunning}
            className="px-6 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-all active:scale-95 flex items-center gap-2 hover:shadow-lg hover:shadow-primary/25"
          >
            {testRunning ? (
              <>
                <Loader2 className="animate-spin" size={14} />
                <span>Running Test Suite...</span>
              </>
            ) : (
              <>
                <Zap size={14} />
                <span>Run E2E Test Suite</span>
              </>
            )}
          </button>
        </div>

        {testError && (
          <div className="bg-red-500/10 border border-red-500/20 text-xs px-4 py-3 rounded-xl text-red-400 font-medium">
            {testError}
          </div>
        )}

        {testRunning && (
          <div className="bg-white/5 border border-white/5 rounded-xl p-6 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="animate-spin text-primary" size={32} />
            <div className="text-center">
              <p className="text-xs font-semibold text-white">Executing End-to-End System Tests...</p>
              <p className="text-[10px] text-textSecondary mt-1">This will ingest a sample project (Opportunity: O-1932849), test multi-hop routing, and teardown automatically.</p>
            </div>
          </div>
        )}

        {testResults && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-textSecondary font-mono">Overall Status</span>
                <span className={`text-lg font-bold mt-2 ${
                  testResults.results?.passed ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {testResults.results?.passed ? '✅ PASSED' : '❌ FAILED'}
                </span>
              </div>
              <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-textSecondary font-mono">Execution Code</span>
                <span className="text-lg font-bold text-white mt-2 font-mono">
                  code {testResults.returncode}
                </span>
              </div>
              <div className="bg-white/5 border border-white/5 rounded-xl p-4 flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-textSecondary font-mono">Checked Steps</span>
                <span className="text-lg font-bold text-white mt-2">
                  {testResults.results?.steps?.length || 0} Steps Verified
                </span>
              </div>
            </div>

            {/* Step List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Verification Steps</h4>
              <div className="divide-y divide-white/5 border border-white/5 rounded-xl overflow-hidden bg-background/50">
                {testResults.results?.steps?.map((step: any, idx: number) => (
                  <div key={idx} className="p-4 flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-white">{step.name}</p>
                      <p className="text-[10px] text-textSecondary font-mono max-w-xl break-all">
                        {typeof step.details === 'object' ? JSON.stringify(step.details) : step.details}
                      </p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      step.status === 'passed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      'bg-red-500/10 text-red-400 border border-red-500/20'
                    }`}>
                      {step.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Routing Table */}
            {testResults.results?.routing_tests?.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">Multi-Agent Chat Routing Checks</h4>
                <div className="overflow-x-auto border border-white/5 rounded-xl bg-background/50">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/5 bg-white/5 text-textSecondary uppercase tracking-wider font-semibold">
                        <th className="p-3">Query</th>
                        <th className="p-3">Expected Agent</th>
                        <th className="p-3">Actual Route</th>
                        <th className="p-3">Agents Inflow</th>
                        <th className="p-3">Verification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-textPrimary/90">
                      {testResults.results.routing_tests.map((rt: any, idx: number) => (
                        <tr key={idx} className="hover:bg-white/5 transition-colors">
                          <td className="p-3 font-medium max-w-[200px] truncate" title={rt.query}>{rt.query}</td>
                          <td className="p-3 font-mono text-[10px] text-accent">{rt.expected_agent || 'N/A'}</td>
                          <td className="p-3 font-mono text-[10px] text-primary">{rt.route_selected || 'N/A'}</td>
                          <td className="p-3 text-[10px] text-textSecondary">{rt.agents_used?.join(' → ') || '-'}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              rt.passed ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              'bg-red-500/10 text-red-400 border border-red-500/20'
                            }`}>
                              {rt.passed ? 'PASS' : 'FAIL'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* Raw Console Logs Toggle */}
            <details className="bg-white/5 border border-white/5 rounded-xl p-4">
              <summary className="text-xs font-semibold text-white cursor-pointer select-none">
                Show Raw Terminal Output / Logs
              </summary>
              <div className="mt-3 bg-black/40 rounded-lg p-4 font-mono text-[10px] text-textSecondary overflow-x-auto max-h-60 space-y-2 whitespace-pre-wrap">
                {testResults.stdout && (
                  <div>
                    <span className="text-primary font-bold">--- STDOUT ---</span>
                    <pre className="mt-1">{testResults.stdout}</pre>
                  </div>
                )}
                {testResults.stderr && (
                  <div className="mt-4">
                    <span className="text-red-400 font-bold">--- STDERR ---</span>
                    <pre className="mt-1">{testResults.stderr}</pre>
                  </div>
                )}
              </div>
            </details>
          </div>
        )}
      </div>

      {/* Danger Zone / Drop Project */}
      <div className="border border-red-500/20 bg-red-950/10 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-start gap-3">
          <Trash2 className="text-red-500 mt-0.5 shrink-0" size={20} />
          <div>
            <h3 className="text-base font-bold text-white">Drop Project</h3>
            <p className="text-xs text-textSecondary mt-1">Permanently delete a project from SQLite, ChromaDB, and remove uploaded files.</p>
          </div>
        </div>

        {feedbackMessage && (
          <div className="bg-white/5 border border-border/40 text-xs px-4 py-2.5 rounded-xl font-mono text-textPrimary">
            {feedbackMessage}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <select
            value={projectToDrop}
            onChange={(e) => setProjectToDrop(e.target.value)}
            className="flex-1 bg-background border border-border rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-red-500/50"
          >
            <option value="">Select a Project to Drop...</option>
            {projects.map(p => (
              <option key={p.project_id} value={p.project_id}>
                {p.customer} ({p.ProjectNumber})
              </option>
            ))}
          </select>

          <button
            onClick={handleDropProject}
            disabled={!projectToDrop || loading}
            className="px-6 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-red-650 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition-all active:scale-95 flex items-center justify-center gap-1.5"
          >
            {loading ? 'Dropping...' : 'Drop Project'}
          </button>
        </div>
      </div>
    </div>
  );
}
