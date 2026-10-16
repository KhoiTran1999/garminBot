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
    <div className="space-y-6 max-w-4xl mx-auto px-4 sm:px-6 py-6">
      {/* Header Material Design 3 Light */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-sky-100 text-sky-700 shrink-0">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Sức khỏe & Đề xuất Tập Luyện</h1>
            <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
              Tổng hợp điểm sẵn sàng, tải tập luyện 7 ngày (TRIMP Banister) và giáo án chi tiết
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-full bg-sky-600 hover:bg-sky-500 px-6 py-2.5 text-xs font-medium text-white shadow-xs hover:shadow transition disabled:opacity-50 shrink-0 active:scale-98"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-white" />
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
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
        <label className="block text-xs font-semibold text-slate-900 mb-2">
          Ghi chú thêm cho HLV hôm nay (Tùy chọn):
        </label>
        <input
          type="text"
          value={userNote}
          onChange={(e) => setUserNote(e.target.value)}
          placeholder="Ví dụ: Hôm nay tôi muốn chạy nhẹ thả lỏng, hoặc: Tôi đang muốn tăng mileage tuần này..."
          className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 transition"
        />
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 flex items-center gap-3">
          <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Active Result */}
      {result ? (
        <div className="space-y-5">
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
        <div className="space-y-5">
          <div className="flex items-center gap-2.5 text-xs text-slate-700 bg-sky-50 p-3.5 rounded-2xl border border-sky-100">
            <Info className="h-4 w-4 text-sky-600 shrink-0" />
            <span>Hiển thị báo cáo lưu gần nhất từ hệ thống. Bấm &quot;Kích hoạt Phân tích Mới&quot; để cập nhật dữ liệu hiện tại.</span>
          </div>
          <ReportViewer 
            report={cachedReport} 
            title="Báo cáo Sức khỏe Đã lưu Gần nhất" 
            modeLabel="Cached Report"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500 shadow-xs">
          <Activity className="h-12 w-12 mx-auto text-slate-300 mb-3" />
          <p className="text-sm font-semibold text-slate-800">Chưa có dữ liệu báo cáo ngày hôm nay</p>
          <p className="text-xs text-slate-500 mt-1.5 max-w-sm mx-auto">Bấm nút &quot;Kích hoạt Phân tích Mới&quot; phía trên để AI bắt đầu phân tích dữ liệu đồng hồ Garmin của bạn.</p>
        </div>
      )}
    </div>
  );
}
