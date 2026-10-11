"use client";

import React, { useState, useEffect } from "react";
import { api, AnalysisResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Flame, Sparkles, RefreshCw, AlertTriangle, Info } from "lucide-react";

export default function WorkoutPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [cachedReport, setCachedReport] = useState<string | null>(null);
  const [userNote, setUserNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getOverview().then((data) => {
      if (data?.recent_reports?.workout) {
        setCachedReport(data.recent_reports.workout);
      }
    }).catch(console.error);
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runAnalysis("workout", userNote);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Lỗi phân tích bài tập. Vui lòng kiểm tra lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20">
            <Flame className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Phân tích Chi tiết Buổi Tập</h1>
            <p className="text-xs text-slate-400">
              Mổ xẻ từng Split km, Vùng nhịp tim (HR Zones), Cardiac Drift và chiến thuật phân bổ sức
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-rose-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-orange-500/20 hover:from-orange-400 hover:to-rose-500 transition disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Đang phân tích bài chạy...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Phân tích Bài tập 24h Qua</span>
            </>
          )}
        </button>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Cảm nhận trong buổi chạy (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Km thứ 8 bị shock hông, hoặc: Bài Tempo hôm nay giữ pace rất đều..."
          className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-orange-500 focus:outline-none"
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
            <AudioPlayer src={result.audio_url} title="Voice Coach - Phân tích bài tập" />
          )}
          <ReportViewer 
            report={result.report} 
            title="Đánh giá Kỹ thuật Buổi tập Chạy" 
            modeLabel="Workout Analysis"
          />
        </div>
      ) : cachedReport ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <Info className="h-4 w-4 text-orange-400 shrink-0" />
            <span>Hiển thị phân tích bài tập gần nhất đã lưu.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Phân tích Bài tập Gần nhất" 
            modeLabel="Cached Workout Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-12 text-center text-slate-400">
          <Flame className="h-10 w-10 mx-auto text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-300">Chưa có phân tích bài tập mới</p>
          <p className="text-xs text-slate-500 mt-1">Đảm bảo đồng hồ Garmin đã đồng bộ buổi chạy mới nhất lên Garmin Connect rồi bấm nút phân tích.</p>
        </div>
      )}
    </div>
  );
}
