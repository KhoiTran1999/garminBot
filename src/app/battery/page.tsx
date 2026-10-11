"use client";

import React, { useState, useEffect } from "react";
import { api, AnalysisResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { AudioPlayer } from "@/components/AudioPlayer";
import { BatteryCharging, Sparkles, RefreshCw, AlertTriangle, Info } from "lucide-react";

export default function BatteryPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [cachedReport, setCachedReport] = useState<string | null>(null);
  const [userNote, setUserNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getOverview().then((data) => {
      if (data?.recent_reports?.battery) {
        setCachedReport(data.recent_reports.battery);
      }
    }).catch(console.error);
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runAnalysis("battery", userNote);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Lỗi phân tích pin năng lượng. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <BatteryCharging className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Bắt mạch Pin Năng Lượng & Stress</h1>
            <p className="text-xs text-slate-400">
              Biểu đồ Body Battery & Mức độ Căng thẳng 2 giờ/block, tìm ra thời điểm hao hụt năng lượng
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 hover:from-emerald-400 hover:to-teal-500 transition disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-slate-950" />
              <span>Đang tính toán biểu đồ...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Phân tích Năng lượng Hôm nay</span>
            </>
          )}
        </button>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Ghi chú công việc / căng thẳng trong ngày (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Buổi chiều họp căng thẳng 3 tiếng, hoặc: Uống 2 cốc cà phê đậm lúc 14h..."
          className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-xs text-red-300 flex items-center gap-3">
          <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result ? (
        <div className="space-y-4">
          {result.audio_url && (
            <AudioPlayer src={result.audio_url} title="Voice Coach - Pin & Căng thẳng" />
          )}
          <ReportViewer 
            report={result.report} 
            title="Đánh giá Mức độ Nạp - Xả Pin Cơ Thể" 
            modeLabel="Battery & Stress Analysis"
          />
        </div>
      ) : cachedReport ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <Info className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>Hiển thị phân tích năng lượng gần nhất đã lưu.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Phân tích Năng lượng Gần nhất" 
            modeLabel="Cached Battery Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-12 text-center text-slate-400">
          <BatteryCharging className="h-10 w-10 mx-auto text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-300">Chưa có phân tích pin năng lượng hôm nay</p>
          <p className="text-xs text-slate-500 mt-1">Bấm nút phía trên để AI rút gọn biểu đồ Body Battery và bắt mạch xu hướng năng lượng của bạn.</p>
        </div>
      )}
    </div>
  );
}
