"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api, AnalysisResult } from "@/lib/api";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { AudioPlayer } from "@/components/AudioPlayer";
import {
  Send,
  Sparkles,
  User,
  Bot,
  AlertCircle,
  RefreshCw,
  Activity,
  Moon,
  Flame,
  BatteryCharging,
  Bandage,
  History,
  Plus,
  X,
  Target
} from "lucide-react";

interface ExtendedChatMessage {
  role: "user" | "assistant";
  content: string;
  audio_url?: string | null;
  mode?: string;
  metrics?: {
    readiness_score?: number | null;
    is_fresh?: boolean;
    fresh_msg?: string;
    date?: string;
  };
}

export default function ChatFirstPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState<{ is_fresh: boolean; message: string } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const quickActionPrompts = [
    {
      id: "daily",
      label: "Hôm nay nên chạy bài gì?",
      icon: Activity,
      color: "text-cyan-400",
      isAnalysis: true,
    },
    {
      id: "sleep_analysis",
      label: "Đánh giá giấc ngủ đêm qua",
      icon: Moon,
      color: "text-indigo-400",
      isAnalysis: true,
    },
    {
      id: "battery",
      label: "Bắt mạch Body Battery",
      icon: BatteryCharging,
      color: "text-emerald-400",
      isAnalysis: true,
    },
    {
      id: "workout",
      label: "Phân tích buổi tập vừa rồi",
      icon: Flame,
      color: "text-orange-400",
      isAnalysis: true,
    },
    {
      id: "rhr_recovery",
      label: "Đánh giá RHR & HRV phục hồi",
      icon: Sparkles,
      color: "text-cyan-300",
      isAnalysis: false,
      text: "Đánh giá nhịp tim nghỉ ngơi (RHR) và độ phục hồi HRV của tôi đêm qua?",
    },
    {
      id: "injury_advice",
      label: "Tư vấn căng cơ & chấn thương",
      icon: Bandage,
      color: "text-rose-400",
      isAnalysis: false,
      text: "Tôi bị mỏi bắp chuối sau buổi chạy hôm qua, hôm nay có nên chạy tiếp không?",
    },
  ];

  useEffect(() => {
    loadChatHistory();

    // Lắng nghe sự kiện mở drawer và đồng bộ từ Navbar
    const handleToggleDrawer = () => setDrawerOpen((prev) => !prev);
    const handleSyncEvent = () => handleCheckSync();

    window.addEventListener("toggle-chat-history", handleToggleDrawer);
    window.addEventListener("refresh-garmin-sync", handleSyncEvent);

    return () => {
      window.removeEventListener("toggle-chat-history", handleToggleDrawer);
      window.removeEventListener("refresh-garmin-sync", handleSyncEvent);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleCheckSync = async () => {
    try {
      const res = await api.getGarminStatus();
      setSyncStatus(res);
    } catch (err: any) {
      setSyncStatus({ is_fresh: false, message: err.message || "Lỗi kiểm tra Garmin" });
    }
  };

  const loadChatHistory = async () => {
    setFetchingHistory(true);
    try {
      const res = await api.getChatHistory();
      if (res.history && res.history.length > 0) {
        setMessages(res.history);
      } else {
        // Welcome message
        setMessages([
          {
            role: "assistant",
            content: `Xin chào ${user?.name || "bạn"}! 👋 Tôi là **Garmin AI Coach** của bạn.\n\nTôi có thể đọc trực tiếp các chỉ số **nhịp tim, giấc ngủ, tải tập luyện TRIMP, HRV và Body Battery** từ đồng hồ Garmin của bạn. Bạn muốn tư vấn bài chạy, kiểm tra thể trạng hay phân tích giấc ngủ hôm nay?`,
          },
        ]);
      }
    } catch (err) {
      console.error("Load chat history error:", err);
    } finally {
      setFetchingHistory(false);
    }
  };

  const handleNewChat = () => {
    setMessages([
      {
        role: "assistant",
        content: `Cuộc trò chuyện mới đã bắt đầu! Bạn muốn hỏi HLV AI về bài tập, giấc ngủ hay thể trạng nào hôm nay?`,
      },
    ]);
    setDrawerOpen(false);
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    setError(null);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const newMsg: ExtendedChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);

    setLoading(true);
    try {
      const res = await api.sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
        },
      ]);
    } catch (err: any) {
      setError(err.message || "Lỗi gửi câu hỏi. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAnalysis = async (mode: string, label: string) => {
    if (loading) return;
    setError(null);

    const userPrompt = `${label}`;
    setMessages((prev) => [...prev, { role: "user", content: userPrompt }]);

    setLoading(true);
    try {
      const result: AnalysisResult = await api.runAnalysis(mode);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.report,
          audio_url: result.audio_url,
          mode: result.mode,
          metrics: result.metrics,
        },
      ]);
    } catch (err: any) {
      setError(err.message || "Lỗi phân tích Garmin. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
  };

  return (
    <div className="flex flex-col flex-1 h-[calc(100dvh-3.25rem)] sm:h-[calc(100dvh-3.5rem)] max-w-4xl mx-auto w-full overflow-hidden bg-slate-950 sm:px-2">
      
      {/* 1. Quick Action Chips Bar (Siêu gọn, cuộn ngang) */}
      <div className="px-3 py-1.5 border-b border-slate-900 bg-slate-950/90 shrink-0 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1 shrink-0 pr-1">
          <Sparkles className="h-3 w-3 text-cyan-400" />
          <span>Gợi ý:</span>
        </span>

        {quickActionPrompts.map((act) => {
          const Icon = act.icon;
          return (
            <button
              key={act.id}
              onClick={() => {
                if (act.isAnalysis) {
                  handleTriggerAnalysis(act.id, act.label);
                } else {
                  handleSend(act.text || act.label);
                }
              }}
              disabled={loading}
              className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-full border border-slate-800 bg-slate-900/80 text-[11px] text-slate-300 hover:text-white hover:border-cyan-500/40 transition disabled:opacity-50"
            >
              <Icon className={`h-3 w-3 ${act.color}`} />
              <span>{act.label}</span>
            </button>
          );
        })}
      </div>

      {/* 2. Messages Stream (Tràn viền, thoáng đãng) */}
      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-3 space-y-3">
        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          return (
            <div
              key={idx}
              className={`flex items-start gap-2 sm:gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${
                  isUser
                    ? "bg-cyan-500 text-slate-950 shadow-sm"
                    : "bg-slate-800 text-cyan-400 border border-slate-700"
                }`}
              >
                {isUser ? <User className="h-3.5 w-3.5 sm:h-4 sm:w-4" /> : <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />}
              </div>

              <div
                className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-3 sm:p-4 text-xs sm:text-sm leading-relaxed space-y-2.5 shadow-sm ${
                  isUser
                    ? "bg-cyan-600 text-white rounded-tr-xs"
                    : "bg-slate-900/90 text-slate-200 border border-slate-800/80 rounded-tl-xs"
                }`}
              >
                {/* Micro-Card Garmin nếu có metrics */}
                {m.metrics && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-2.5 rounded-xl bg-slate-950/90 border border-slate-800/80 text-xs">
                    {m.metrics.readiness_score !== undefined && m.metrics.readiness_score !== null && (
                      <div>
                        <span className="text-[10px] text-slate-400 block">Sẵn sàng</span>
                        <span className="font-bold text-amber-400">
                          {m.metrics.readiness_score}/100
                        </span>
                      </div>
                    )}
                    <div>
                      <span className="text-[10px] text-slate-400 block">Garmin</span>
                      <span className={`font-semibold ${m.metrics.is_fresh ? "text-emerald-400" : "text-amber-400"}`}>
                        {m.metrics.is_fresh ? "Đã đồng bộ" : "Chờ đồng bộ"}
                      </span>
                    </div>
                    {m.metrics.date && (
                      <div>
                        <span className="text-[10px] text-slate-400 block">Ngày</span>
                        <span className="font-medium text-white">{m.metrics.date}</span>
                      </div>
                    )}
                    {m.mode && (
                      <div>
                        <span className="text-[10px] text-slate-400 block">Chế độ</span>
                        <span className="font-medium text-cyan-400 uppercase">{m.mode}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Markdown text content */}
                {isUser ? (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                ) : (
                  <MarkdownRenderer content={m.content} />
                )}

                {/* Audio Player nhúng */}
                {m.audio_url && (
                  <div className="pt-2 border-t border-slate-800/80">
                    <AudioPlayer src={m.audio_url} title={`Voice Coach - ${m.mode ? m.mode.toUpperCase() : "HLV AI"}`} />
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {loading && (
          <div className="flex items-start gap-2 sm:gap-2.5">
            <div className="flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-cyan-400 border border-slate-700">
              <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </div>
            <div className="rounded-2xl rounded-tl-xs border border-slate-800 bg-slate-900/90 p-3 sm:p-3.5 text-xs text-slate-300 flex items-center gap-2 shadow-sm">
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
              <span>HLV AI đang tra cứu Garmin và phân tích...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-3 mb-2 p-2.5 rounded-xl border border-red-800 bg-red-950/60 text-xs text-red-300 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-1.5">
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white p-1">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* 3. Bottom Input Bar (Dính sát đáy, gọn gàng) */}
      <div className="p-2 sm:p-2.5 border-t border-slate-900 bg-slate-950/95 shrink-0 z-20">
        <div className="flex items-end gap-1.5 bg-slate-900/90 border border-slate-800 rounded-2xl px-3 py-1.5 focus-within:border-cyan-500 transition shadow-lg">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi HLV AI điều gì đó..."
            rows={1}
            className="w-full resize-none bg-transparent py-1 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none max-h-24"
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="flex h-8 w-8 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 hover:bg-cyan-400 disabled:opacity-30 transition shadow-sm shrink-0 mb-0.5"
            title="Gửi câu hỏi"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>

        <p className="hidden sm:block text-[10px] text-slate-500 text-center mt-1">
          HLV AI tự động tra cứu dữ liệu nhịp tim, HRV, giấc ngủ thời gian thực từ Garmin Connect.
        </p>
      </div>

      {/* 4. History Drawer Modal */}
      {drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            className="fixed inset-0 bg-black/60 z-40 backdrop-blur-xs transition-opacity"
          />
          <div className="fixed inset-y-0 left-0 w-72 max-w-[80vw] bg-slate-950 border-r border-slate-800 z-50 p-4 flex flex-col shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Lịch sử Hội thoại</h3>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <button
              onClick={handleNewChat}
              className="flex items-center justify-center gap-1.5 w-full py-2 px-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs mb-3 transition shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Cuộc trò chuyện mới</span>
            </button>

            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 text-xs">
              <div
                onClick={() => setDrawerOpen(false)}
                className="p-2.5 rounded-xl bg-slate-900 border border-cyan-500/30 text-white cursor-pointer hover:bg-slate-800 transition flex items-center justify-between"
              >
                <div className="truncate flex-1 pr-2">
                  <span className="font-semibold block truncate">Phiên hiện tại</span>
                  <span className="text-[10px] text-cyan-400">{messages.length} tin nhắn</span>
                </div>
                <div className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              </div>

              <div className="pt-3 border-t border-slate-800/80">
                <button
                  onClick={() => {
                    loadChatHistory();
                    setDrawerOpen(false);
                  }}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border border-slate-800 text-[11px] text-slate-400 hover:text-white hover:bg-slate-900 transition"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Tải lại từ máy chủ</span>
                </button>
              </div>
            </div>

            {/* Athlete Quick Status in Drawer */}
            <div className="pt-2.5 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-300">
                <Target className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                <span className="truncate">{user?.goal || "Chưa thiết lập mục tiêu"}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
