import { useState, useEffect } from 'react';
import { ShieldAlert, Check, X, Loader2, Info, ChevronDown, ChevronUp } from 'lucide-react';
import axios from 'axios';

type ApprovalItem = {
  approval_id: string;
  project_id: string;
  approval_type: string;
  status: string;
  description: string;
  requested_by_agent: string;
  requested_at: string;
  proposed_changes?: any;
};

export default function ApprovalQueue() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const fetchApprovals = async () => {
    try {
      setIsLoading(true);
      setErrorMsg('');
      const res = await axios.get('http://localhost:8000/api/agents/approvals/pending');
      setItems(res.data);
    } catch (error) {
      console.error('Failed to fetch approvals:', error);
      setErrorMsg('Failed to load pending agent approval requests.');
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
      <div className="flex-1 flex flex-col items-center justify-center h-96 gap-3">
        <Loader2 className="animate-spin text-primary w-10 h-10" />
        <span className="text-xs text-textSecondary font-semibold">Loading agent queues...</span>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto h-full flex flex-col space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
          🛡️ Approval Center
        </h1>
        <p className="text-textSecondary mt-2">Review and authorize pending autonomous agent actions before execution.</p>
      </header>

      {errorMsg && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-xs flex items-center gap-2">
          <ShieldAlert size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Info Tip */}
      <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 flex items-start gap-2.5 text-xs text-textSecondary">
        <Info className="shrink-0 text-primary mt-0.5" size={16} />
        <div>
          <span className="font-semibold text-primary">Human-In-The-Loop Security:</span> Autonomous agents require explicit developer or manager authorization whenever they propose modifying baseline forecasts or executing project deletes.
        </div>
      </div>

      <div className="space-y-4">
        {items.length === 0 ? (
          <div className="glass-panel p-12 rounded-2xl text-center border-dashed border-2 border-border/50 bg-surface/20">
            <ShieldAlert className="mx-auto text-textSecondary mb-3 opacity-60" size={32} />
            <p className="text-textSecondary font-medium">All caught up! No pending agent actions require approval.</p>
          </div>
        ) : (
          items.map(item => {
            const isExpanded = expandedItems[item.approval_id] !== false;
            const hasWps = item.approval_type === 'WorkPackageIngestion' && Array.isArray(item.proposed_changes);
            const hasRaid = item.approval_type === 'RaidItemCreation' && item.proposed_changes;
            
            return (
              <div 
                key={item.approval_id} 
                className="glass-panel p-6 rounded-2xl flex flex-col gap-6 border-l-4 border-l-amber-500 hover:border-l-amber-400 transition-all duration-300 relative overflow-hidden group"
              >
                {/* Decorative accent glow */}
                <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl group-hover:bg-amber-500/10 transition-colors"></div>

                 <div className="flex flex-col md:flex-row gap-6 items-start md:items-center w-full">
                  <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0 shadow-sm">
                    <ShieldAlert size={22} className="text-amber-500 animate-pulse" />
                  </div>
                  
                  <div className="flex-1 space-y-2 relative z-10">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[9px] font-mono font-bold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        PENDING AUTHORIZATION
                      </span>
                      <span className="text-[10px] font-mono text-textSecondary bg-background/50 px-2.5 py-0.5 rounded border border-border">
                        Project: {item.project_id}
                      </span>
                      <span className="text-[10px] text-textSecondary">
                        Requested by: <span className="text-primary font-bold">{item.requested_by_agent}</span>
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white tracking-tight">{item.approval_type}</h3>
                    <p className="text-xs text-textSecondary leading-relaxed">
                      {item.description}
                    </p>
                    
                    {(hasWps || hasRaid) && (
                      <button
                        onClick={() => toggleExpand(item.approval_id)}
                        className="mt-2 text-primary hover:text-primaryLight flex items-center gap-1 text-xs font-semibold focus:outline-none cursor-pointer"
                      >
                        {isExpanded ? (
                          <>Hide details <ChevronUp size={14} /></>
                        ) : (
                          <>Show details <ChevronDown size={14} /></>
                        )}
                      </button>
                    )}
                  </div>

                  <div className="flex gap-2.5 w-full md:w-auto mt-4 md:mt-0 shrink-0 relative z-10">
                    <button 
                      onClick={() => handleResolve(item.approval_id, 'Rejected')}
                      className="flex-1 md:flex-none btn-secondary border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 flex items-center justify-center gap-1.5 cursor-pointer text-xs py-2 px-4"
                    >
                      <X size={14} /> Reject
                    </button>
                    <button 
                      onClick={() => handleResolve(item.approval_id, 'Approved')}
                      className="flex-1 md:flex-none btn-primary flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 hover:shadow-emerald-500/20 border border-emerald-500/50 cursor-pointer text-xs py-2 px-4"
                    >
                      <Check size={14} /> Authorize
                    </button>
                  </div>
                </div>

                {/* Proposed RAID Item preview */}
                {hasRaid && isExpanded && (
                  <div className="mt-2 border-t border-border/40 pt-4 w-full text-xs space-y-3 z-10 relative">
                    <h4 className="font-bold text-white text-sm mb-2 flex items-center gap-1.5">
                      Proposed RAID Item Details
                    </h4>
                    <div className="bg-background/40 p-4 rounded-xl border border-border/50 hover:border-border transition-colors">
                      <div className="flex justify-between items-center mb-1 pb-1 border-b border-border/30">
                        <span className="font-bold text-primary text-sm flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            item.proposed_changes.item_type === 'Risk' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                            item.proposed_changes.item_type === 'Issue' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                            item.proposed_changes.item_type === 'Dependency' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                            'bg-green-500/10 text-green-400 border border-green-500/20'
                          }`}>
                            {item.proposed_changes.item_type}
                          </span>
                          <span className="text-textSecondary">•</span>
                          <span className="text-textPrimary">{item.proposed_changes.category} Category</span>
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3 text-textSecondary text-[11px] leading-relaxed">
                        <div className="col-span-1 md:col-span-3">
                          <strong className="text-white block mb-0.5">📝 Description:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary text-xs whitespace-pre-wrap">{item.proposed_changes.description}</p>
                        </div>
                        {item.proposed_changes.mitigating_action && (
                          <div className="col-span-1 md:col-span-3">
                            <strong className="text-white block mb-0.5">🛡️ Mitigating Action / Response Plan:</strong>
                            <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary text-xs whitespace-pre-wrap">{item.proposed_changes.mitigating_action}</p>
                          </div>
                        )}
                        <div>
                          <strong className="text-white block mb-0.5">👤 Owner:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">{item.proposed_changes.owner || "Unassigned"}</p>
                        </div>
                        <div>
                          <strong className="text-white block mb-0.5">📅 Due Date:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">{item.proposed_changes.due_date || "N/A"}</p>
                        </div>
                        <div>
                          <strong className="text-white block mb-0.5">🛡️ ROAM Status:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">{item.proposed_changes.roam || "Mitigated"}</p>
                        </div>
                        <div>
                          <strong className="text-white block mb-0.5">🎯 Impact Area:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">{item.proposed_changes.impact_area || "None"}</p>
                        </div>
                        <div>
                          <strong className="text-white block mb-0.5">💵 Financial Impact:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">
                            {item.proposed_changes.financial_impact ? `$${item.proposed_changes.financial_impact.toLocaleString()}` : "$0.00"}
                          </p>
                        </div>
                        <div>
                          <strong className="text-white block mb-0.5">⏳ Schedule Impact Days:</strong>
                          <p className="bg-background/30 p-2 rounded border border-border/30 text-textPrimary font-semibold">
                            {item.proposed_changes.schedule_impact_days ? `${item.proposed_changes.schedule_impact_days} days` : "0 days"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Proposed Work Packages preview */}
                {hasWps && isExpanded && (
                  <div className="mt-2 border-t border-border/40 pt-4 w-full text-xs space-y-3 z-10 relative">
                    <h4 className="font-bold text-white text-sm mb-2 flex items-center gap-1.5">
                      Proposed Work Packages ({item.proposed_changes.length})
                    </h4>
                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                      {item.proposed_changes.map((wp: any, idx: number) => (
                        <div key={idx} className="bg-background/40 p-4 rounded-xl border border-border/50 hover:border-border transition-colors">
                          <div className="flex justify-between items-center mb-1 pb-1 border-b border-border/30">
                            <span className="font-bold text-primary text-sm">WP #{wp.phase_order}: {wp.phase_name}</span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 text-textSecondary text-[11px] leading-relaxed">
                            {wp.overview && (
                              <div className="col-span-1 md:col-span-2">
                                <strong className="text-white block mb-0.5">ℹ️ Overview:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap text-textPrimary">{wp.overview}</p>
                              </div>
                            )}
                            {wp.quick_summary && (
                              <div className="col-span-1 md:col-span-2">
                                <strong className="text-white block mb-0.5">⚡ Quick Summary:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap text-textPrimary">{wp.quick_summary}</p>
                              </div>
                            )}
                            <div>
                              <strong className="text-white block mb-0.5">📋 Activities:</strong>
                              <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.activities || "N/A"}</p>
                            </div>
                            <div>
                              <strong className="text-white block mb-0.5">📦 Deliverables:</strong>
                              <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.deliverables || "N/A"}</p>
                            </div>
                            <div>
                              <strong className="text-white block mb-0.5">🔑 Prerequisites:</strong>
                              <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.prerequisites || "N/A"}</p>
                            </div>
                            {wp.customer_responsibilities && (
                              <div>
                                <strong className="text-white block mb-0.5">🤝 Customer Responsibilities:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.customer_responsibilities}</p>
                              </div>
                            )}
                            {wp.scope && (
                              <div>
                                <strong className="text-white block mb-0.5">🎯 Scope:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.scope}</p>
                              </div>
                            )}
                            {wp.tech_landscape && (
                              <div>
                                <strong className="text-white block mb-0.5">🌐 Tech Landscape:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.tech_landscape}</p>
                              </div>
                            )}
                            {wp.engagement_summary && (
                              <div>
                                <strong className="text-white block mb-0.5">💼 Engagement Summary:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.engagement_summary}</p>
                              </div>
                            )}
                            {wp.key_deliverables && (
                              <div>
                                <strong className="text-white block mb-0.5">🚚 Key Deliverables:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.key_deliverables}</p>
                              </div>
                            )}
                            {wp.missing_items && (
                              <div>
                                <strong className="text-white block mb-0.5">🔍 Missing Items:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap text-amber-400">{wp.missing_items}</p>
                              </div>
                            )}
                            {wp.next_steps && (
                              <div>
                                <strong className="text-white block mb-0.5">🚀 Next Steps:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap text-emerald-400">{wp.next_steps}</p>
                              </div>
                            )}
                            {wp.out_of_scope && (
                              <div>
                                <strong className="text-white block mb-0.5">🚫 Out of Scope:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.out_of_scope}</p>
                              </div>
                            )}
                            {wp.risks_mitigations && (
                              <div>
                                <strong className="text-white block mb-0.5">⚠️ Risks & Mitigations:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.risks_mitigations}</p>
                              </div>
                            )}
                            {wp.acceptance_criteria && (
                              <div className="col-span-1 md:col-span-2">
                                <strong className="text-white block mb-0.5">✅ Acceptance Criteria:</strong>
                                <p className="bg-background/30 p-2 rounded border border-border/30 whitespace-pre-wrap">{wp.acceptance_criteria}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
