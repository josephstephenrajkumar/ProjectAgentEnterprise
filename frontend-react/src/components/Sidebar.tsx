import { Link, useLocation } from 'react-router-dom';
import { Settings, MessageSquare, PlusSquare, Database, Trash2 } from 'lucide-react';

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
  { name: 'Chat', path: '/chat', icon: MessageSquare },
  { name: 'Create Project', path: '/create-project', icon: PlusSquare },
  { name: 'Data Manager', path: '/data-manager', icon: Database },
];

const stackInfo = [
  { label: 'LLM', value: 'Groq / Cloud' },
  { label: 'Orchestrator', value: 'LangGraph' },
  { label: 'Vector DB', value: 'ChromaDB' },
  { label: 'Gateway', value: 'Node.js' },
  { label: 'Embeddings', value: 'all-mpnet-base-v2' },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-72 h-screen border-r border-border bg-surface flex flex-col custom-scrollbar overflow-y-auto">
      <div className="p-5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent to-primary flex items-center justify-center shadow-lg shadow-primary/20">
          <Settings size={18} className="text-white animate-[spin_4s_linear_infinite]" />
        </div>
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          OpenClaw
          <span className="text-[10px] font-bold bg-primary text-white px-1.5 py-0.5 rounded-full">v3</span>
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
            <button className="w-full flex items-center gap-3 px-3 py-2 text-sm bg-background border border-border rounded-lg text-textSecondary hover:text-red-400 hover:border-red-500/50 transition-all">
              <Trash2 size={16} /> Clear Chat
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
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* STACK SECTION */}
        <div className="mt-auto mb-4">
          <h2 className="text-[10px] font-bold text-textSecondary uppercase tracking-widest mb-3">Stack</h2>
          <div className="space-y-2 border-t border-border/50 pt-3">
            {stackInfo.map((info) => (
              <div key={info.label} className="flex justify-between items-center text-[11px]">
                <span className="text-textSecondary">{info.label}</span>
                <span className="text-primary font-medium">{info.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      
    </aside>
  );
}
