"use client";

import React, { useState, useEffect } from "react";
import { api, AnalysisResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Activity, Sparkles, RefreshCw, AlertTriangle, Info } from "lucide-react";

export default function DailyPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [cachedReport, setCachedReport] = useState<string | null>(null);
  const [userNote, setUserNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load cached report if any
    api.getOverview().then((data) => {
      if (data?.recent_reports?.daily) {
        setCachedReport(data.recent_reports.daily);
      }
    }).catch(console.error);
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runAnalysis("daily", userNote);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Lỗi tạo báo cáo. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Sức khỏe & Đề xuất Tập Luyện</h1>
            <p className="text-xs text-slate-400">
              Tổng hợp điểm sẵn sàng, tải tập luyện 7 ngày (TRIMP Banister) và giáo án chi tiết
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-slate-950" />
              <span>Đang phân tích Garmin & AI...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>Kích hoạt Phân tích Mới</span>
            </>
          )}
        </button>
      </div>

      {/* Athlete note */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Ghi chú thêm cho HLV hôm nay (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Hôm nay tôi muốn chạy nhẹ thả lỏng, hoặc: Tôi đang muốn tăng mileage tuần này..."
          className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
        />
      </div>

      {error && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-xs text-red-300 flex items-center gap-3">
          <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Result */}
      {result ? (
        <div className="space-y-4">
          {result.audio_url && (
            <AudioPlayer src={result.audio_url} title="Voice Coach - Báo cáo ngày" />
          )}
          <ReportViewer 
            report={result.report} 
            title="Giáo án & Báo cáo Sức khỏe Hôm nay" 
            modeLabel="Daily Report"
          />
        </div>
      ) : cachedReport ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <Info className="h-4 w-4 text-cyan-400 shrink-0" />
            <span>Hiển thị báo cáo lưu gần nhất từ hệ thống. Bấm &quot;Kích hoạt Phân tích Mới&quot; để cập nhật dữ liệu hiện tại.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Báo cáo Sức khỏe Đã lưu Gần nhất" 
            modeLabel="Cached Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-12 text-center text-slate-400">
          <Activity className="h-10 w-10 mx-auto text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-300">Chưa có dữ liệu báo cáo ngày hôm nay</p>
          <p className="text-xs text-slate-500 mt-1">Bấm nút &quot;Kích hoạt Phân tích Mới&quot; phía trên để AI bắt đầu phân tích dữ liệu đồng hồ Garmin của bạn.</p>
        </div>
      )}
    </div>
  );
}
