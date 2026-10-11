"use client";

import React, { useState, useEffect } from "react";
import { api, AnalysisResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Moon, Sparkles, RefreshCw, AlertTriangle, Info } from "lucide-react";

export default function SleepPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [cachedReport, setCachedReport] = useState<string | null>(null);
  const [userNote, setUserNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getOverview().then((data) => {
      if (data?.recent_reports?.sleep) {
        setCachedReport(data.recent_reports.sleep);
      }
    }).catch(console.error);
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runAnalysis("sleep_analysis", userNote);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Lỗi phân tích giấc ngủ. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Moon className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Phân tích Chuyên sâu Giấc Ngủ</h1>
            <p className="text-xs text-slate-400">
              Đánh giá Deep, Light, REM sleep, nhịp tim nghỉ ngơi (RHR), SpO2 và độ phục hồi
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-400 hover:to-purple-500 transition disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Đang phân tích giấc ngủ...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Phân tích Giấc ngủ Đêm qua</span>
            </>
          )}
        </button>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Ghi chú thêm về cảm giác thức dậy (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Đêm qua hơi chập chờn, hoặc: Sáng dậy thấy rất tỉnh táo sảng khoái..."
          className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
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
            <AudioPlayer src={result.audio_url} title="Voice Coach - Giấc ngủ & Phục hồi" />
          )}
          <ReportViewer 
            report={result.report} 
            title="Đánh giá Chi tiết Giấc ngủ Đêm qua" 
            modeLabel="Sleep Analysis"
          />
        </div>
      ) : cachedReport ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <Info className="h-4 w-4 text-indigo-400 shrink-0" />
            <span>Hiển thị phân tích giấc ngủ gần nhất đã lưu.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Phân tích Giấc ngủ Gần nhất" 
            modeLabel="Cached Sleep Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-12 text-center text-slate-400">
          <Moon className="h-10 w-10 mx-auto text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-300">Chưa có phân tích giấc ngủ cho ngày hôm nay</p>
          <p className="text-xs text-slate-500 mt-1">Bấm nút phía trên để AI đọc dữ liệu ngủ đêm qua từ Garmin Connect.</p>
        </div>
      )}
    </div>
  );
}
