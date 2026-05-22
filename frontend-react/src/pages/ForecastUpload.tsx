import React, { useState, useEffect } from 'react';
import { UploadCloud, FileSpreadsheet, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';

type Project = {
  project_id: string;
  ProjectNumber: string;
  customer: string;
};

export default function ForecastUpload() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [reportingMonth, setReportingMonth] = useState('');
  const [comments, setComments] = useState('');
  const [file, setFile] = useState<File | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [fetchingProjects, setFetchingProjects] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [uploadResult, setUploadResult] = useState<any>(null);

  // Set default reporting month to current month YYYY-MM
  useEffect(() => {
    const d = new Date();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    setReportingMonth(`${d.getFullYear()}-${month}`);
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setFetchingProjects(true);
      const res = await axios.get('http://localhost:8000/api/projects');
      setProjects(res.data);
      if (res.data.length > 0) {
        setSelectedProjectId(res.data[0].project_id);
      }
    } catch (err) {
      console.error('Error fetching projects:', err);
    } finally {
      setFetchingProjects(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError('');
      setSuccess(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) {
      setError('Please select a project.');
      return;
    }
    if (!reportingMonth) {
      setError('Please select a reporting month.');
      return;
    }
    if (!file) {
      setError('Please select a forecast Excel file.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);
    setUploadResult(null);

    const formData = new FormData();
    // Convert YYYY-MM to YYYY-MM-01 format required by database schema
    const formattedMonth = `${reportingMonth}-01`;
    formData.append('reporting_month', formattedMonth);
    formData.append('submitted_by', 'PM');
    formData.append('comments', comments);
    formData.append('file', file);

    try {
      const res = await axios.post(
        `http://localhost:8000/api/projects/${selectedProjectId}/forecast-upload`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setSuccess(true);
      setUploadResult(res.data);
      setComments('');
      setFile(null);
      // Reset input element
      const fileInput = document.getElementById('excel-file') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to upload and process forecast file.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Upload Forecast</h1>
        <p className="text-textSecondary mt-2">Submit monthly PM reforecasts via Excel template.</p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6 glass-panel rounded-2xl p-8 shadow-2xl">
        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-4 rounded-xl flex items-start gap-3">
            <CheckCircle2 className="shrink-0 mt-0.5" size={18} />
            <div>
              <p className="font-semibold">Forecast Uploaded Successfully!</p>
              <p className="text-xs opacity-80 mt-1">
                Version #{uploadResult?.version_number} was created as "{uploadResult?.version_name}". Status: {uploadResult?.status}.
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-start gap-3">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <div>
              <p className="font-semibold">Upload Failed</p>
              <p className="text-xs opacity-80 mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
              Select Project *
            </label>
            {fetchingProjects ? (
              <div className="h-12 bg-background/50 border border-border rounded-xl flex items-center px-4">
                <Loader2 className="animate-spin text-primary mr-2" size={16} />
                <span className="text-xs text-textSecondary">Loading projects...</span>
              </div>
            ) : (
              <select
                value={selectedProjectId}
                onChange={(e) => {
                  setSelectedProjectId(e.target.value);
                  setSuccess(false);
                  setError('');
                }}
                className="w-full bg-background border border-border rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
                required
              >
                {projects.length === 0 ? (
                  <option value="">No projects found. Create one first!</option>
                ) : (
                  projects.map(p => (
                    <option key={p.project_id} value={p.project_id}>
                      {p.customer} ({p.ProjectNumber})
                    </option>
                  ))
                )}
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
              Reporting Month *
            </label>
            <input
              type="month"
              value={reportingMonth}
              onChange={(e) => setReportingMonth(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
            Comments
          </label>
          <textarea
            placeholder="Describe the adjustments in this reforecast..."
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            rows={3}
            className="w-full bg-background border border-border rounded-xl px-4 py-3 text-white placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all text-sm"
          />
        </div>

        <div className="border-t border-border/50 pt-6">
          <label className="block text-xs font-bold text-textSecondary uppercase tracking-widest mb-2">
            📊 Select Excel Forecast Template (.xlsx) *
          </label>
          
          <div className="relative border-2 border-dashed border-border/60 hover:border-primary/40 rounded-xl p-8 flex flex-col items-center justify-center bg-background/20 transition-all cursor-pointer group">
            <input
              type="file"
              accept=".xlsx"
              id="excel-file"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              required
            />
            
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <UploadCloud size={24} className="text-primary" />
            </div>

            <p className="text-sm font-semibold text-white">
              {file ? file.name : 'Select file or drag it here'}
            </p>
            <p className="text-[10px] text-textSecondary mt-1">
              {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Only Excel spreadsheets (.xlsx) are accepted'}
            </p>
          </div>
        </div>

        <div className="pt-4">
          <button
            type="submit"
            disabled={loading || projects.length === 0}
            className="w-fit flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary to-accent hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl font-medium shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 active:scale-95 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={18} />
                Processing Forecast...
              </>
            ) : (
              <>
                <FileSpreadsheet size={18} />
                Upload Forecast Version
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
