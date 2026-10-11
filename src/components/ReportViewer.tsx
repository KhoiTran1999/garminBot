"use client";

import React, { useState } from "react";
import { Copy, Check, FileText } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ReportViewerProps {
  report: string;
  title?: string;
  modeLabel?: string;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({ 
  report, 
  title = "Báo cáo Huấn luyện viên AI",
  modeLabel = "Chi tiết"
}) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3.5 bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <FileText className="h-4 w-4 text-cyan-400" />
          <span className="text-sm font-semibold text-white">{title}</span>
          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300">
            {modeLabel}
          </span>
        </div>

        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Đã sao chép</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Sao chép</span>
            </>
          )}
        </button>
      </div>

      <div className="p-6 overflow-x-auto">
        <MarkdownRenderer content={report} />
      </div>
    </div>
  );
};
