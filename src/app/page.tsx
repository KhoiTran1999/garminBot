"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api, AnalysisResult } from "@/lib/api";
import { ReportViewer } from "@/components/ReportViewer";
import { AudioPlayer } from "@/components/AudioPlayer";
import { 
  Activity, 
  Moon, 
  Flame, 
  BatteryCharging, 
  MessageSquare, 
  RefreshCw, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle,
  Wind,
  Target,
  Bandage,
  ChevronRight
} from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<any>(null);
  const [syncStatus, setSyncStatus] = useState<{ is_fresh: boolean; message: string } | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [userNote, setUserNote] = useState("");
  
  // Execution state
  const [runningMode, setRunningMode] = useState<string | null>(null);
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    try {
      const data = await api.getOverview();
      setOverview(data);
    } catch (err) {
      console.error("Load overview error:", err);
    }
  };

  const handleCheckSync = async () => {
    setSyncLoading(true);
    try {
      const res = await api.getGarminStatus();
      setSyncStatus(res);
    } catch (err: any) {
      setSyncStatus({ is_fresh: false, message: err.message || "Lỗi kiểm tra Garmin" });
    } finally {
      setSyncLoading(false);
    }
  };

  const handleTriggerAnalysis = async (mode: string) => {
    setRunningMode(mode);
    setErrorMsg(null);
    setCurrentResult(null);

    try {
      const result = await api.runAnalysis(mode, userNote);
      setCurrentResult(result);
      loadOverview();
    } catch (err: any) {
      setErrorMsg(err.message || "Lỗi phân tích. Vui lòng thử lại.");
    } finally {
      setRunningMode(null);
    }
  };

  const actions = [
    {
      id: "daily",
      name: "Sức khỏe & Đề xuất tập",
      desc: "Tính điểm sẵn sàng, Acute Load 7 ngày (TRIMP), AQI và lên giáo án chạy hôm nay",
      icon: Activity,
      gradient: "from-cyan-500/20 to-blue-500/10",
      border: "border-cyan-500/30",
      accent: "text-cyan-400",
      pageHref: "/daily"
    },
    {
      id: "sleep_analysis",
      name: "Phân tích Giấc ngủ",
      desc: "Mổ xẻ 3 pha ngủ (Deep, Light, REM), RHR, SpO2, nhịp thở và chất lượng phục hồi đêm qua",
      icon: Moon,
      gradient: "from-indigo-500/20 to-purple-500/10",
      border: "border-indigo-500/30",
      accent: "text-indigo-400",
      pageHref: "/sleep"
    },
    {
      id: "workout",
      name: "Phân tích Buổi tập",
      desc: "Phân tích bài tập trong 24h: Splits, HR Zone, nhịp tim trôi dạt (cardiac drift), pacing",
      icon: Flame,
      gradient: "from-orange-500/20 to-rose-500/10",
      border: "border-orange-500/30",
      accent: "text-orange-400",
      pageHref: "/workout"
    },
    {
      id: "battery",
      name: "Bắt mạch Năng lượng",
      desc: "Phân tích biểu đồ Body Battery & Stress theo khung 2 giờ, tìm nguyên nhân cạn kiệt pin",
      icon: BatteryCharging,
      gradient: "from-emerald-500/20 to-teal-500/10",
      border: "border-emerald-500/30",
      accent: "text-emerald-400",
      pageHref: "/battery"
    },
  ];

  const todayStr = new Intl.DateTimeFormat("vi-VN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());

  return (
    <div className="space-y-8">
      {/* Hero / Welcome Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 p-6 md:p-8 shadow-2xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-semibold text-cyan-400 border border-cyan-500/20">
                {todayStr}
              </span>
              {overview?.weather && (
                <span className="flex items-center gap-1 rounded-full bg-slate-800/80 px-2.5 py-1 text-xs text-slate-300">
                  <Wind className="h-3.5 w-3.5 text-cyan-400" />
                  AQI: {overview.weather.aqi || 45} ({overview.weather.status || "Tốt"})
                </span>
              )}
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Xin chào, <span className="text-cyan-400">{user?.name || "Vận động viên"}</span>! 👋
            </h1>
            <p className="mt-2 text-xs md:text-sm text-slate-400 max-w-2xl leading-relaxed">
              Trợ lý Huấn luyện viên AI cá nhân hóa của bạn đã sẵn sàng. Chọn tính năng bên dưới để phân tích thể trạng và nhận giáo án tập luyện hôm nay.
            </p>
          </div>

          {/* Sync Button & Profile quick info */}
          <div className="flex flex-col sm:flex-row md:flex-col items-start md:items-end gap-3 shrink-0">
            <button
              onClick={handleCheckSync}
              disabled={syncLoading}
              className="flex items-center gap-2 rounded-xl bg-slate-800/90 hover:bg-slate-800 px-4 py-2.5 text-xs font-semibold text-white border border-slate-700/80 transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncLoading ? "animate-spin text-cyan-400" : ""}`} />
              <span>{syncLoading ? "Đang kiểm tra Garmin..." : "Kiểm tra Đồng bộ Garmin"}</span>
            </button>

            {syncStatus && (
              <div className={`flex items-center gap-1.5 text-xs ${syncStatus.is_fresh ? "text-emerald-400" : "text-amber-400"}`}>
                {syncStatus.is_fresh ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                <span>{syncStatus.message}</span>
              </div>
            )}
          </div>
        </div>

        {/* User Goals / Injury Badges */}
        <div className="mt-6 pt-6 border-t border-slate-800/80 flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <Target className="h-4 w-4 text-cyan-400" />
            <span className="text-slate-400">Mục tiêu:</span>
            <span className="font-semibold text-white">{user?.goal || "Chưa thiết lập"}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Bandage className="h-4 w-4 text-rose-400" />
            <span className="text-slate-400">Tình trạng cơ thể:</span>
            <span className="font-semibold text-white">{user?.injury || "Khỏe mạnh"}</span>
          </div>
          <Link href="/profile" className="text-cyan-400 hover:underline text-xs flex items-center gap-0.5 ml-auto">
            Chỉnh sửa trên Notion <ChevronRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      {/* Optional athlete note input */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <label className="block text-xs font-semibold text-slate-300 mb-2 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-cyan-400" />
          Nhắn nhủ thêm với AI cho lần phân tích này (Tùy chọn):
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={userNote}
            onChange={(e) => setUserNote(e.target.value)}
            placeholder="Ví dụ: Hôm nay tôi muốn chạy nhẹ thả lỏng, hoặc: Tôi thấy hơi mỏi cơ bắp chuối trái..."
            className="flex-1 rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
          {userNote && (
            <button
              onClick={() => setUserNote("")}
              className="px-3 py-2 text-xs text-slate-400 hover:text-white"
            >
              Xóa
            </button>
          )}
        </div>
      </div>

      {/* Quick Action Grid */}
      <div>
        <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <span>Kích hoạt Phân tích 1-Chạm</span>
          <span className="text-xs font-normal text-slate-400">(Tự động kéo dữ liệu Garmin & chạy AI)</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {actions.map((act) => {
            const Icon = act.icon;
            const isRunning = runningMode === act.id;

            return (
              <div
                key={act.id}
                className={`relative overflow-hidden rounded-xl border ${act.border} bg-gradient-to-br ${act.gradient} p-5 shadow-lg flex flex-col justify-between transition-all hover:border-slate-600`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-lg bg-slate-950/60 ${act.accent}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <h3 className="text-sm font-bold text-white">{act.name}</h3>
                    </div>

                    <Link
                      href={act.pageHref}
                      className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                    >
                      Chi tiết <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    {act.desc}
                  </p>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleTriggerAnalysis(act.id)}
                    disabled={runningMode !== null}
                    className={`w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-bold transition shadow-md ${
                      isRunning
                        ? "bg-cyan-500 text-slate-950"
                        : "bg-slate-900/90 text-white hover:bg-slate-800 border border-slate-700/80"
                    } disabled:opacity-50`}
                  >
                    {isRunning ? (
                      <>
                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                        <span>Đang phân tích dữ liệu Garmin & AI...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Phân tích ngay</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Analysis Error Message */}
      {errorMsg && (
        <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-xs text-red-300 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Live Result Display */}
      {currentResult && (
        <div className="space-y-4 pt-4 border-t border-slate-800">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Kết quả Phân tích Vừa tạo</span>
            </h2>
          </div>

          {/* Voice Coach Audio Note if available */}
          {currentResult.audio_url && (
            <AudioPlayer src={currentResult.audio_url} title={`Voice Coach - ${currentResult.mode.toUpperCase()}`} />
          )}

          {/* Structured Report */}
          <ReportViewer 
            report={currentResult.report} 
            title={`Báo cáo ${currentResult.mode.toUpperCase()}`} 
            modeLabel={currentResult.mode}
          />
        </div>
      )}

      {/* Direct AI Chat Promotion */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <MessageSquare className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Bạn muốn hỏi thêm HLV điều gì?</h3>
            <p className="text-xs text-slate-400">Trò chuyện 2 chiều với AI Coach, tra cứu các chỉ số sức khỏe Garmin trong quá khứ.</p>
          </div>
        </div>
        <Link
          href="/chat"
          className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold transition shadow-md shadow-cyan-500/20"
        >
          <span>Mở phòng Chat HLV</span>
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
