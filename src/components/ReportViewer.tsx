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
    <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-3.5 bg-slate-50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-sky-100 text-sky-700">
            <FileText className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold text-slate-900">{title}</span>
          <span className="rounded-full bg-sky-100 px-2.5 py-0.5 text-[11px] font-medium text-sky-800">
            {modeLabel}
          </span>
        </div>

        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-sky-700 hover:bg-slate-100 transition"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-600" />
              <span className="text-emerald-600 font-medium">Đã sao chép</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Sao chép</span>
            </>
          )}
        </button>
      </div>

      <div className="p-6 overflow-x-auto text-slate-800">
        <MarkdownRenderer content={report} />
      </div>
    </div>
  );
};
