import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, CheckCircle, AlertCircle, Loader2, FileText, 
  BarChart2, FileSpreadsheet 
} from 'lucide-react';
import axios from 'axios';

export default function CreateProject() {
  const [projectName, setProjectName] = useState('');
  const [projectCode, setProjectCode] = useState('');
  const [opportunityId, setOpportunityId] = useState('');
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [estimationFile, setEstimationFile] = useState<File | null>(null);
  const [projectFile, setProjectFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Polling state for background vectorization status
  const [pollingProjectId, setPollingProjectId] = useState<string | null>(null);
  const [vectorizationStatus, setVectorizationStatus] = useState<string>('idle');
  const [vectorizationError, setVectorizationError] = useState<string>('');
  const [pollCount, setPollCount] = useState(0);

  const intervalRef = useRef<any>(null);

  useEffect(() => {
    if (pollingProjectId) {
      setVectorizationStatus('processing');
      setVectorizationError('');
      setPollCount(0);

      intervalRef.current = setInterval(async () => {
        try {
          const res = await axios.get(`http://localhost:8000/api/projects/${pollingProjectId}`);
          const status = res.data.vectorization_status || 'idle';
          const errorMsg = res.data.vectorization_error || '';

          setVectorizationStatus(status);
          setPollCount(prev => prev + 1);
          
          if (status === 'completed' || status === 'failed') {
            if (intervalRef.current) {
              clearInterval(intervalRef.current);
            }
            if (status === 'failed') {
              setVectorizationError(errorMsg);
            }
          }
        } catch (err) {
          console.error('Error polling project status:', err);
        }
      }, 5000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [pollingProjectId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName || !projectCode || !contractFile || !estimationFile) {
      setError('Please fill in all required fields and upload the SOW and estimation files.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);
    setPollingProjectId(null);
    setVectorizationStatus('idle');
    setVectorizationError('');

    const formData = new FormData();
    formData.append('project_name', projectName);
    formData.append('project_code', projectCode);
    if (opportunityId) formData.append('opportunity_id', opportunityId);
    formData.append('contract_file', contractFile);
    formData.append('estimation_file', estimationFile);
    if (projectFile) formData.append('project_file', projectFile);

    try {
      const response = await axios.post('http://localhost:8000/api/projects', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccess(true);
      
      const newProjectId = response.data.project_id;
      setPollingProjectId(newProjectId);

      setProjectName('');
      setProjectCode('');
      setOpportunityId('');
      setContractFile(null);
      setEstimationFile(null);
      setProjectFile(null);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to trigger project ingestion pipeline.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = () => {
    setProjectName('Boston SMAX Migration');
    setProjectCode('BOSTON-001');
    setOpportunityId('O-1932849');
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
          📁 Project Ingestion Cockpit
        </h1>
        <p className="text-textSecondary mt-2">Initialize new projects by linking opportunity IDs and parsing SOW estimation files.</p>
      </header>

      <form onSubmit={handleSubmit} className="dual-panel-grid">
        
        {/* LEFT PANEL: Metadata inputs */}
        <div className="glass-panel p-6 rounded-2xl space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-bold text-white uppercase tracking-wider">Project Metadata</h3>
            <button
              type="button"
              onClick={handleQuickFill}
              className="text-[10px] font-bold text-primary hover:text-indigo-400 bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
            >
              ⚡ Quick Fill (O-1932849)
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
                Project Name *
              </label>
              <input
                type="text"
                placeholder="e.g. Boston SMAX Migration"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="form-input-field"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
                  Project Code *
                </label>
                <input
                  type="text"
                  placeholder="e.g. BOSTON-001"
                  value={projectCode}
                  onChange={(e) => setProjectCode(e.target.value)}
                  className="form-input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
                  Opportunity ID
                </label>
                <input
                  type="text"
                  placeholder="e.g. O-1932849"
                  value={opportunityId}
                  onChange={(e) => setOpportunityId(e.target.value)}
                  className="form-input-field"
                />
              </div>
            </div>
          </div>

          {/* Verification / Progress status inside Left Panel */}
          {(success || vectorizationStatus !== 'idle') && (
            <div className="border-t border-border pt-5 space-y-4">
              <h4 className="text-xs font-bold text-white uppercase tracking-widest">Ingestion Pipeline Monitor</h4>
              
              {success && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-3 rounded-xl flex items-start gap-2.5 text-xs">
                  <CheckCircle className="shrink-0 mt-0.5" size={15} />
                  <div>
                    <p className="font-semibold">Project Ingestion Triggered</p>
                    <p className="opacity-80 text-[10px]">Record registered. Background parsing schedules initiated.</p>
                  </div>
                </div>
              )}

              {vectorizationStatus !== 'idle' && (
                <div className={`p-4 rounded-xl border text-xs space-y-3 ${
                  vectorizationStatus === 'processing' ? 'bg-primary/5 border-primary/20 text-textSecondary' :
                  vectorizationStatus === 'completed' ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300' :
                  'bg-red-500/5 border-red-500/20 text-red-300'
                }`}>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-white">ChromaDB Vectorization Status:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-textSecondary font-mono">(Polled {pollCount} times)</span>
                      <span className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        vectorizationStatus === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                        vectorizationStatus === 'failed' ? 'bg-red-500/10 text-red-400 animate-pulse' :
                        'bg-primary/10 text-primary animate-pulse'
                      }`}>
                        {vectorizationStatus}
                      </span>
                    </div>
                  </div>

                  {vectorizationStatus === 'processing' && (
                    <div className="space-y-2 pt-2 border-t border-border/30">
                      <div className="flex items-center gap-2 text-[10px] text-textSecondary">
                        <Loader2 className="animate-spin text-primary shrink-0" size={12} />
                        <span>Parsing SOW text and estimating tables...</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-textSecondary">
                        <Loader2 className="animate-spin text-accent shrink-0" size={12} />
                        <span>Chunking and running embedding models...</span>
                      </div>
                    </div>
                  )}

                  {vectorizationStatus === 'completed' && (
                    <p className="text-[10px] text-emerald-400">
                      ✅ SOW context parsed and indexed in vector space. Agents can now answer project deliverable questions.
                    </p>
                  )}

                  {vectorizationStatus === 'failed' && (
                    <p className="text-[10px] text-red-400 font-semibold">
                      ❌ Failed: {vectorizationError || 'Vector database process faulted.'}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-xs flex items-start gap-2.5">
              <AlertCircle className="shrink-0 mt-0.5" size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-gradient-to-r from-primary to-accent hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl font-bold shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 active:scale-95 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  <span>Submitting Ingestion Packet...</span>
                </>
              ) : (
                <>
                  <Plus size={18} />
                  <span>Create Project & Ingest Files</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* RIGHT PANEL: File Drag zones */}
        <div className="glass-panel p-6 rounded-2xl space-y-5 flex flex-col justify-between">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white uppercase tracking-wider">Collections Upload</h3>
            <p className="text-xs text-textSecondary">Select documents to populate database tables and RAG memory layers.</p>
          </div>

          <div className="space-y-4">
            
            {/* CONTRACT UPLOAD CARD */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider">📄 SOW Contract (.docx/.pdf) *</span>
                {contractFile && <span className="text-[10px] text-emerald-400 font-semibold">Ready</span>}
              </div>
              <div className={`dropzone-box ${contractFile ? 'active' : ''}`}>
                <input
                  type="file"
                  accept=".docx,.doc,.pdf"
                  onChange={(e) => setContractFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="sow-contract-picker"
                />
                <FileText size={22} className={contractFile ? 'text-emerald-400' : 'text-textSecondary'} />
                <span className="text-xs font-semibold text-white mt-1.5 max-w-full truncate">
                  {contractFile ? contractFile.name : 'Select SOW document'}
                </span>
                <span className="text-[9px] text-textSecondary mt-0.5">
                  {contractFile ? `${(contractFile.size / 1024).toFixed(1)} KB` : 'Engagement, terms, pricing limits'}
                </span>
              </div>
            </div>

            {/* ESTIMATION UPLOAD CARD */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider">📊 Excel Estimates (.xlsx) *</span>
                {estimationFile && <span className="text-[10px] text-emerald-400 font-semibold">Ready</span>}
              </div>
              <div className={`dropzone-box ${estimationFile ? 'active' : ''}`}>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setEstimationFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="estimation-picker"
                />
                <BarChart2 size={22} className={estimationFile ? 'text-emerald-400' : 'text-textSecondary'} />
                <span className="text-xs font-semibold text-white mt-1.5 max-w-full truncate">
                  {estimationFile ? estimationFile.name : 'Select Estimation spreadsheet'}
                </span>
                <span className="text-[9px] text-textSecondary mt-0.5">
                  {estimationFile ? `${(estimationFile.size / 1024).toFixed(1)} KB` : 'Resource schedules, Travel & Expense costs'}
                </span>
              </div>
            </div>

            {/* PROJECT ERP METADATA UPLOAD CARD (OPTIONAL) */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-textSecondary uppercase tracking-wider">🗃️ ERP Metadata (.xlsx) – Optional</span>
                {projectFile && <span className="text-[10px] text-emerald-400 font-semibold">Linked</span>}
              </div>
              <div className={`dropzone-box ${projectFile ? 'active' : ''}`}>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setProjectFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="erp-picker"
                />
                <FileSpreadsheet size={22} className={projectFile ? 'text-emerald-400' : 'text-textSecondary'} />
                <span className="text-xs font-semibold text-white mt-1.5 max-w-full truncate">
                  {projectFile ? projectFile.name : 'Select ERP spreadsheet'}
                </span>
                <span className="text-[9px] text-textSecondary mt-0.5">
                  {projectFile ? `${(projectFile.size / 1024).toFixed(1)} KB` : 'Optional ERP codes, milestones, financials'}
                </span>
              </div>
            </div>

          </div>

          <div className="pt-2 text-center">
            <span className="text-[10px] text-textSecondary italic">
              All uploads are isolated per project ID and stored securely.
            </span>
          </div>
        </div>

      </form>
    </div>
  );
}
