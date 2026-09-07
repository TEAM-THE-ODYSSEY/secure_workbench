import React, { useState } from 'react';
import { FileText, FileSpreadsheet, Presentation, Download, X, Loader2, CheckCircle2 } from 'lucide-react';
import { apiFetch } from '../../utils/api';

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'report' | 'summary';
  messageText: string;
  sources?: Array<{ title: string; category?: string; meta?: string; badge?: string }>;
}

export const ExportReportModal: React.FC<ExportReportModalProps> = ({
  isOpen,
  onClose,
  initialMode = 'report',
  messageText,
  sources = [],
}) => {
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'docx' | 'pptx'>('pdf');
  const [mode, setMode] = useState<'report' | 'summary'>(initialMode);
  const [isExporting, setIsExporting] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    setIsExporting(true);
    setDownloadSuccess(null);

    try {
      const titleStr = mode === 'summary' ? 'MRPL Executive Summary' : 'MRPL Operational Report';
      const response = await apiFetch('/api/v1/export/document', {
        method: 'POST',
        body: JSON.stringify({
          format: selectedFormat,
          title: titleStr,
          mode: mode,
          content: messageText,
          sources: sources,
        }),
      });

      if (!response.ok) {
        throw new Error(`Export failed with HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const ext = selectedFormat;
      const fileName = `${mode === 'summary' ? 'MRPL_Summary' : 'MRPL_Report'}_${new Date().toISOString().slice(0, 10)}.${ext}`;

      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setDownloadSuccess(`Successfully generated ${fileName}`);
      setTimeout(() => {
        setDownloadSuccess(null);
        onClose();
      }, 1800);
    } catch (err: any) {
      console.error('Document export error:', err);
      alert(`Export failed: ${err.message || 'Server error'}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#1b4332] text-white flex items-center justify-center font-bold text-sm shadow-xs">
              <FileText className="w-5 h-5 text-emerald-300" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">Export & Download Report</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Select document format and export mode</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Mode Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
              Report Type
            </label>
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 dark:bg-slate-800/60 rounded-xl">
              <button
                type="button"
                onClick={() => setMode('report')}
                className={`py-2 px-3 text-xs font-medium rounded-lg transition-all ${
                  mode === 'report'
                    ? 'bg-white dark:bg-[#1b4332] text-[#1b4332] dark:text-white shadow-xs font-bold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                📄 Full Operational Report
              </button>
              <button
                type="button"
                onClick={() => setMode('summary')}
                className={`py-2 px-3 text-xs font-medium rounded-lg transition-all ${
                  mode === 'summary'
                    ? 'bg-white dark:bg-[#1b4332] text-[#1b4332] dark:text-white shadow-xs font-bold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                📊 Executive Summary
              </button>
            </div>
          </div>

          {/* Format Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
              Select Output Format
            </label>
            <div className="space-y-2.5">
              {/* PDF Option */}
              <button
                type="button"
                onClick={() => setSelectedFormat('pdf')}
                className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  selectedFormat === 'pdf'
                    ? 'border-[#1b4332] dark:border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/40 ring-2 ring-[#1b4332]/20 dark:ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-red-100 text-red-600 dark:bg-red-950/60 dark:text-red-400 flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">PDF Document (.pdf)</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">MRPL branded document with tables & citations</div>
                  </div>
                </div>
                {selectedFormat === 'pdf' && <div className="w-2.5 h-2.5 rounded-full bg-[#1b4332] dark:bg-emerald-400" />}
              </button>

              {/* DOCX Option */}
              <button
                type="button"
                onClick={() => setSelectedFormat('docx')}
                className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  selectedFormat === 'docx'
                    ? 'border-[#1b4332] dark:border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/40 ring-2 ring-[#1b4332]/20 dark:ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400 flex items-center justify-center">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">Word Document (.docx)</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">Editable Microsoft Word report with formatted headings</div>
                  </div>
                </div>
                {selectedFormat === 'docx' && <div className="w-2.5 h-2.5 rounded-full bg-[#1b4332] dark:bg-emerald-400" />}
              </button>

              {/* PPTX Option */}
              <button
                type="button"
                onClick={() => setSelectedFormat('pptx')}
                className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                  selectedFormat === 'pptx'
                    ? 'border-[#1b4332] dark:border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/40 ring-2 ring-[#1b4332]/20 dark:ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-orange-100 text-orange-600 dark:bg-orange-950/60 dark:text-orange-400 flex items-center justify-center">
                    <Presentation className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">PowerPoint Slide Deck (.pptx)</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">16:9 presentation slides formatted for briefings</div>
                  </div>
                </div>
                {selectedFormat === 'pptx' && <div className="w-2.5 h-2.5 rounded-full bg-[#1b4332] dark:bg-emerald-400" />}
              </button>
            </div>
          </div>

          {/* Success Message */}
          {downloadSuccess && (
            <div className="p-3 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 rounded-xl text-xs flex items-center gap-2 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>{downloadSuccess}</span>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <button
            type="button"
            onClick={onClose}
            disabled={isExporting}
            className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className="px-5 py-2 text-xs font-bold text-white bg-[#1b4332] hover:bg-[#165528] active:bg-[#12421f] rounded-xl flex items-center gap-2 transition-all shadow-md disabled:opacity-50 cursor-pointer"
          >
            {isExporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating {selectedFormat.toUpperCase()}...</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Download {selectedFormat.toUpperCase()}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
