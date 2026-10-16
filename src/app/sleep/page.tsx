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
    <div className="space-y-6 max-w-4xl mx-auto px-4 sm:px-6 py-6">
      {/* Header Material Design 3 Light */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-indigo-100 text-indigo-700 shrink-0">
            <Moon className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Phân tích Chuyên sâu Giấc Ngủ</h1>
            <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
              Đánh giá Deep, Light, REM sleep, nhịp tim nghỉ ngơi (RHR), SpO2 và độ phục hồi
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-full bg-indigo-600 hover:bg-indigo-500 px-6 py-2.5 text-xs font-medium text-white shadow-xs hover:shadow transition disabled:opacity-50 shrink-0 active:scale-98"
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

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
        <label className="block text-xs font-semibold text-slate-900 mb-2">
          Ghi chú thêm về cảm giác thức dậy (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Đêm qua hơi chập chờn, hoặc: Sáng dậy thấy rất tỉnh táo sảng khoái..."
          className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition"
        />
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center gap-3">
          <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {result ? (
        <div className="space-y-5">
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
        <div className="space-y-5">
          <div className="flex items-center gap-2.5 text-xs text-slate-700 bg-indigo-50 p-3.5 rounded-2xl border border-indigo-100">
            <Info className="h-4 w-4 text-indigo-600 shrink-0" />
            <span>Hiển thị phân tích giấc ngủ gần nhất đã lưu.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Phân tích Giấc ngủ Gần nhất" 
            modeLabel="Cached Sleep Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500 shadow-xs">
          <Moon className="h-12 w-12 mx-auto text-slate-300 mb-3" />
          <p className="text-sm font-semibold text-slate-800">Chưa có phân tích giấc ngủ cho ngày hôm nay</p>
          <p className="text-xs text-slate-500 mt-1.5 max-w-sm mx-auto">Bấm nút phía trên để AI đọc dữ liệu ngủ đêm qua từ Garmin Connect.</p>
        </div>
      )}
    </div>
  );
}
