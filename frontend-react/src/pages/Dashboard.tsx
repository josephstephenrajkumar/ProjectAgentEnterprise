export default function Dashboard() {
  return (
    <div className="h-full flex flex-col">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Project Dashboard</h1>
        <p className="text-textSecondary mt-2">Overview of financial health and active forecasts.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Mock Metric Cards */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <span className="text-sm font-medium text-textSecondary uppercase tracking-wider">Total Revenue EAC</span>
          <span className="text-4xl font-bold text-white mt-4">$12.4M</span>
          <div className="mt-4 flex items-center text-sm text-secondary">
            <span className="bg-secondary/10 px-2 py-1 rounded-md">+4.2% from Baseline</span>
          </div>
        </div>
        
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <span className="text-sm font-medium text-textSecondary uppercase tracking-wider">Gross Margin</span>
          <span className="text-4xl font-bold text-white mt-4">24.8%</span>
          <div className="mt-4 flex items-center text-sm text-red-400">
            <span className="bg-red-400/10 px-2 py-1 rounded-md">-1.2% from Baseline</span>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <span className="text-sm font-medium text-textSecondary uppercase tracking-wider">Active Risks</span>
          <span className="text-4xl font-bold text-white mt-4">12</span>
          <div className="mt-4 flex items-center text-sm text-textSecondary">
            <span className="bg-white/5 px-2 py-1 rounded-md border border-white/10">3 High Priority</span>
          </div>
        </div>
      </div>

      <div className="flex-1 glass-panel rounded-2xl p-8 flex items-center justify-center border-dashed border-2 border-border/50 bg-surface/20">
        <div className="text-center">
          <h3 className="text-xl font-semibold text-textPrimary mb-2">Detailed Analytics Coming Soon</h3>
          <p className="text-textSecondary max-w-md mx-auto">
            The reporting module is currently being connected to the new SQLite analytics engine.
          </p>
        </div>
      </div>
    </div>
  );
}
