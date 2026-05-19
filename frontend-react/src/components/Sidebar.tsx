import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, UploadCloud, CheckSquare } from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Agent Chat', path: '/chat', icon: MessageSquare },
  { name: 'Forecast Upload', path: '/forecast', icon: UploadCloud },
  { name: 'Approval Queue', path: '/approvals', icon: CheckSquare },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 h-screen border-r border-border bg-surface/50 backdrop-blur-xl flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          ProjectAgent
          <span className="block text-sm font-medium text-textSecondary mt-1">Enterprise Edition</span>
        </h1>
      </div>
      
      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          
          return (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                isActive 
                  ? 'bg-primary/10 text-primary shadow-sm shadow-primary/5' 
                  : 'text-textSecondary hover:bg-white/5 hover:text-textPrimary'
              }`}
            >
              <Icon size={20} className={isActive ? 'text-primary' : 'text-textSecondary group-hover:text-textPrimary transition-colors'} />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-border/50">
        <div className="flex items-center gap-3 px-4 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent to-primary flex items-center justify-center text-sm font-bold text-white shadow-lg">
            PA
          </div>
          <div>
            <p className="text-sm font-medium text-textPrimary">System Agent</p>
            <p className="text-xs text-secondary flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-secondary inline-block"></span>
              Online
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
