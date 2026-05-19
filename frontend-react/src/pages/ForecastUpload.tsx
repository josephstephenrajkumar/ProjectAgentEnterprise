import { UploadCloud, FileSpreadsheet } from 'lucide-react';

export default function ForecastUpload() {
  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Upload Forecast</h1>
        <p className="text-textSecondary mt-2">Submit monthly PM reforecasts via Excel template.</p>
      </header>

      <div className="glass-panel rounded-2xl p-10 flex flex-col items-center justify-center flex-1 border-dashed border-2 border-primary/30 bg-surface/40 hover:bg-surface/60 transition-colors cursor-pointer group">
        <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
          <UploadCloud size={40} className="text-primary" />
        </div>
        
        <h3 className="text-xl font-bold text-white mb-2">Drag and drop your Excel file here</h3>
        <p className="text-textSecondary text-center max-w-md mb-8">
          Upload the standard PM Forecast Template (.xlsx). The system will automatically parse resources, milestones, and trigger variance analysis.
        </p>

        <button className="btn-primary flex items-center gap-2 px-6 py-3">
          <FileSpreadsheet size={18} />
          Select Excel File
        </button>
      </div>
    </div>
  );
}
