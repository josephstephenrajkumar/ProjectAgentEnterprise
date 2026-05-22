import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Settings, MessageSquare, PlusSquare, Database, Trash2, 
  ShieldAlert, Cpu, Server, Network, Braces, Terminal, Layers 
} from 'lucide-react';
import axios from 'axios';

const agentMesh = [
  { name: 'Plan-Forecast Agent', color: 'bg-primary' },
  { name: 'Contract Agent', color: 'bg-primary' },
  { name: 'General Agent', color: 'bg-primary' },
  { name: 'Synthesizer (Both)', color: 'bg-orange-500' },
  { name: 'Project Creation', color: 'bg-secondary' },
  { name: 'Delete Project Agent', color: 'bg-transparent' },
  { name: 'Pricing Agent', color: 'bg-transparent' },
  { name: 'Risk Agent', color: 'bg-orange-500' },
  { name: 'RAID Update', color: 'bg-primary' },
];

const navItems = [
  { name: 'Chat Cockpit', path: '/chat', icon: MessageSquare },
  { name: 'Project Ingestion', path: '/create-project', icon: PlusSquare },
  { name: 'Data Manager', path: '/data-manager', icon: Database },
  { name: 'Approval Center', path: '/approvals', icon: ShieldAlert },
];

const stackInfo = [
  { label: 'UI / Presentation', value: 'React 18 + Vite (TS)', icon: Braces, color: 'text-sky-400' },
  { label: 'API Services', value: 'FastAPI (Python 3.12)', icon: Server, color: 'text-emerald-400' },
  { label: 'Agent Orchestrator', value: 'LangGraph Workflows', icon: Terminal, color: 'text-indigo-400' },
  { label: 'RAG Query Engine', value: 'LlamaIndex Core', icon: Layers, color: 'text-pink-500' },
  { label: 'RAG Ingestion Layer', value: 'LangChain Community', icon: Layers, color: 'text-pink-400' },
  { label: 'Embedding Model', value: 'HuggingFace (MiniLM)', icon: Cpu, color: 'text-orange-400' },
  { label: 'Core LLM Engine', value: 'Llama 3.3 70B (Groq)', icon: Cpu, color: 'text-amber-400' },
  { label: 'Write Database', value: 'SQLite Relational (SSOT)', icon: Database, color: 'text-blue-400' },
  { label: 'Graph Projection', value: 'KuzuDB (CQRS Graph)', icon: Network, color: 'text-purple-400' },
  { label: 'Vector Index', value: 'ChromaDB (RAG Memory)', icon: Database, color: 'text-teal-400' },
];

export default function Sidebar() {
  const location = useLocation();
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    const fetchPendingCount = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/agents/approvals/pending');
        setPendingCount(res.data.length);
      } catch (err) {
        console.error('Error fetching pending approvals:', err);
      }
    };
    fetchPendingCount();
    const interval = setInterval(fetchPendingCount, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleClearChat = async () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      try {
        await axios.post('http://localhost:8000/api/chat/clear', { session_id: 'default' });
        window.location.reload();
      } catch (err) {
        console.error('Failed to clear chat:', err);
      }
    }
  };

  const handleResetDatabase = async () => {
    const confirm1 = window.confirm(
      '🚨 WARNING: This will permanently delete all projects, work packages, milestones, financial actuals, approvals, and chat history. This action CANNOT be undone.\n\nAre you sure you want to perform a full system reset?'
    );
    if (!confirm1) return;

    const confirm2 = window.prompt(
      'To confirm database reset, please type "RESET" in the box below:'
    );
    if (confirm2 !== 'RESET') {
      alert('Reset cancelled: verification text did not match.');
      return;
    }

    try {
      const res = await axios.post('http://localhost:8000/api/projects/database/reset');
      alert(res.data.message || 'Database reset completed successfully.');
      window.location.reload();
    } catch (err: any) {
      console.error('Failed to reset database:', err);
      alert('Error resetting database: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <aside className="w-72 h-screen border-r border-border bg-surface flex flex-col custom-scrollbar overflow-y-auto">
      <div className="p-5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent to-primary flex items-center justify-center shadow-lg shadow-primary/20">
          <Settings size={18} className="text-white animate-[spin_4s_linear_infinite]" />
        </div>
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          Program Co-pilot
        </h1>
      </div>
      
      <div className="px-5 py-3 flex-1 flex flex-col gap-6">
        
        {/* AGENT MESH SECTION */}
        <div>
          <h2 className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-3">Agent Mesh</h2>
          <ul className="space-y-2">
            {agentMesh.map((agent) => (
              <li key={agent.name} className="flex items-center gap-3 text-sm text-textPrimary/80 hover:text-white cursor-pointer transition-colors">
                <span className={`w-2 h-2 rounded-full ${agent.color === 'bg-transparent' ? 'border border-textSecondary' : agent.color}`}></span>
                {agent.name}
              </li>
            ))}
          </ul>
          
          <div className="mt-4 space-y-2">
            <button className="w-full flex items-center gap-3 px-3 py-2 text-sm bg-background border border-border rounded-lg text-textSecondary hover:text-white hover:border-primary/50 transition-all">
              <Database size={16} /> Re-Ingest Docs
            </button>
            <button 
              onClick={handleClearChat}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm bg-background border border-border rounded-lg text-textSecondary hover:text-red-400 hover:border-red-500/50 transition-all cursor-pointer"
            >
              <Trash2 size={16} /> Clear Chat
            </button>
            <button 
              onClick={handleResetDatabase}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm bg-background border border-border rounded-lg text-textSecondary hover:text-red-400 hover:border-red-500/50 transition-all cursor-pointer"
            >
              <Trash2 size={16} className="text-red-400" /> Reset Database
            </button>
          </div>
        </div>


        {/* NAVIGATION SECTION */}
        <div>
          <h2 className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-3">Navigation</h2>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (location.pathname === '/' && item.path === '/chat');
              
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive 
                      ? 'bg-primary text-white shadow-lg shadow-primary/25' 
                      : 'text-textSecondary hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <Icon size={18} className={isActive ? 'text-white' : 'text-textSecondary'} />
                  <span className="flex-1">{item.name}</span>
                  {item.path === '/approvals' && pendingCount > 0 && (
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500 text-black rounded-full animate-pulse">
                      {pendingCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* STACK SECTION */}
        <div className="mt-auto pt-4 border-t border-border/50">
          <h2 className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <Layers size={10} className="text-primary animate-pulse" />
            System Stack Layers
          </h2>
          <div className="space-y-2.5">
            {stackInfo.map((info) => {
              const Icon = info.icon;
              return (
                <div key={info.label} className="flex items-start gap-2.5 bg-background/40 p-2 rounded-lg border border-border/30 hover:border-border transition-colors">
                  <div className={`p-1.5 bg-surface rounded border border-border/50 shrink-0 ${info.color}`}>
                    <Icon size={12} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] text-textSecondary font-semibold uppercase tracking-wider leading-none mb-1">{info.label}</div>
                    <div className="text-[11px] text-white font-medium truncate leading-none">{info.value}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      
    </aside>
  );
}
