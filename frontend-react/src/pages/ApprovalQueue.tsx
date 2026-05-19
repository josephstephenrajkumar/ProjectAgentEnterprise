import { useState, useEffect } from 'react';
import { ShieldAlert, Check, X, Loader2 } from 'lucide-react';
import axios from 'axios';

type ApprovalItem = {
  approval_id: string;
  project_id: string;
  approval_type: string;
  status: string;
  description: string;
  requested_by_agent: string;
  requested_at: string;
};

export default function ApprovalQueue() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchApprovals();
  }, []);

  const fetchApprovals = async () => {
    try {
      setIsLoading(true);
      const res = await axios.get('http://localhost:8000/api/agents/approvals/pending');
      setItems(res.data);
    } catch (error) {
      console.error('Failed to fetch approvals:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async (id: string, action: 'Approved' | 'Rejected') => {
    try {
      await axios.post(`http://localhost:8000/api/agents/approvals/${id}/resolve`, {
        action,
        resolved_by: 'Admin User'
      });
      // Optimistically remove from list
      setItems(prev => prev.filter(item => item.approval_id !== id));
    } catch (error) {
      console.error(`Failed to ${action} approval:`, error);
      alert(`Failed to ${action} item. Check console.`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-primary w-10 h-10" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto h-full flex flex-col">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Human Approval Queue</h1>
        <p className="text-textSecondary mt-2">Review and authorize pending autonomous agent actions.</p>
      </header>

      <div className="space-y-4">
        {items.length === 0 ? (
          <div className="glass-panel p-10 rounded-2xl text-center border-dashed border-2 border-border/50 bg-surface/20">
            <p className="text-textSecondary font-medium">All caught up! No pending approvals.</p>
          </div>
        ) : (
          items.map(item => (
            <div key={item.approval_id} className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row gap-6 items-start md:items-center border-l-4 border-l-amber-500">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                <ShieldAlert size={24} className="text-amber-500" />
              </div>
              
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xs font-mono font-bold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    PENDING APPROVAL
                  </span>
                  <span className="text-xs font-mono text-textSecondary bg-surface px-2 py-0.5 rounded border border-border">
                    Project: {item.project_id}
                  </span>
                  <span className="text-xs text-textSecondary">
                    Agent: <span className="text-primary">{item.requested_by_agent}</span>
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mb-1">{item.approval_type}</h3>
                <p className="text-sm text-textSecondary leading-relaxed">
                  {item.description}
                </p>
              </div>

              <div className="flex gap-3 w-full md:w-auto mt-4 md:mt-0 shrink-0">
                <button 
                  onClick={() => handleResolve(item.approval_id, 'Rejected')}
                  className="flex-1 md:flex-none btn-secondary border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 flex items-center justify-center gap-2"
                >
                  <X size={16} /> Reject
                </button>
                <button 
                  onClick={() => handleResolve(item.approval_id, 'Approved')}
                  className="flex-1 md:flex-none btn-primary flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 hover:shadow-emerald-500/20 border border-emerald-500/50"
                >
                  <Check size={16} /> Authorize
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
